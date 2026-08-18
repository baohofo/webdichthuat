import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import CANONICAL_STAGE_ORDER, MIN_VALID_AUDIO_BYTES, RUNTIME_INSTANCE_ID, JOBS_DIR
from backend.utils.file_utils import get_job_paths

logger = logging.getLogger("job_store")

# Task Registry theo dõi in-memory các Background Tasks đang thực thi (Invariant 6)
ACTIVE_BACKGROUND_TASKS: Dict[str, asyncio.Task] = {}


def register_active_task(job_id: str, task: asyncio.Task) -> None:
    ACTIVE_BACKGROUND_TASKS[job_id] = task


def unregister_active_task(job_id: str) -> None:
    ACTIVE_BACKGROUND_TASKS.pop(job_id, None)


def get_active_task(job_id: str) -> Optional[asyncio.Task]:
    return ACTIVE_BACKGROUND_TASKS.get(job_id)


STAGE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "upload": {"label": "Tải video lên", "weight": 5},
    "metadata": {"label": "Đọc metadata video", "weight": 5},
    "extract_audio": {"label": "Tách giọng & trích xuất Dual Audio", "weight": 10},
    "stt": {"label": "Whisper STT - Nhận dạng giọng nói", "weight": 25},
    "translation": {"label": "Gemini AI - Dịch thuật ngữ cảnh", "weight": 15},
    "tts": {"label": "AI Voice TTS - Tổng hợp giọng đọc", "weight": 20},
    "audio_sync": {"label": "Đồng bộ & Lồng tiếng timeline", "weight": 5},
    "subtitle": {"label": "Tạo & Cân bằng phụ đề SRT", "weight": 5},
    "render": {"label": "Render Video hoàn chỉnh (H.264 + AAC 48kHz)", "weight": 10},
}

CONFIG_DEPENDENCIES: Dict[str, List[str]] = {
    # Voice & Speech synthesis settings
    "voice_id": ["tts", "audio_sync", "render"],
    "speed_rate": ["tts", "audio_sync", "render"],
    "pitch": ["tts", "audio_sync", "render"],

    # Audio Mixing settings
    "voice_volume": ["render"],
    "background_volume": ["render"],
    "keep_background_audio": ["render"],

    # Subtitle & Mask settings
    "subtitle_style": ["subtitle", "render"],
    "subtitle_enabled": ["subtitle", "render"],
    "subtitle_mode": ["subtitle", "render"],
    "burn_subtitles": ["subtitle", "render"],
    "create_subtitle": ["subtitle", "render"],
    "mask_regions": ["render"],

    # Resolution & Output format
    "output_resolution": ["render"],
    "output_format": ["render"],

    # Translation settings
    "translation_style": ["translation", "tts", "audio_sync", "subtitle", "render"],
    "target_language": ["translation", "tts", "audio_sync", "subtitle", "render"],
    "source_language": ["stt", "translation", "tts", "audio_sync", "subtitle", "render"],

    # STT Whisper settings
    "whisper_model": ["stt", "translation", "tts", "audio_sync", "subtitle", "render"],
}

_JOB_LOCKS: Dict[str, asyncio.Lock] = {}


def _get_job_lock(job_id: str) -> asyncio.Lock:
    if job_id not in _JOB_LOCKS:
        _JOB_LOCKS[job_id] = asyncio.Lock()
    return _JOB_LOCKS[job_id]


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_dirty_stages(
    old_config: Optional[Dict[str, Any]],
    new_config: Dict[str, Any],
    current_stages: Dict[str, Any],
) -> List[str]:
    """
    So sánh cấu hình cũ và cấu hình mới theo CONFIG_DEPENDENCIES để xác định chính xác danh sách các stage bị dirty.
    - Nếu old_config là rỗng hoặc chưa từng chạy thành công: dirty toàn bộ các stage được bật.
    - Nếu thay đổi config: Chỉ đánh dấu dirty các downstream stages tương ứng.
    - Nếu một stage chưa 'completed' trên đĩa: Stage đó và các downstream stages mặc định là dirty.
    - Kết quả trả về được sắp xếp theo CANONICAL_STAGE_ORDER.
    """
    if not old_config:
        return [s for s in CANONICAL_STAGE_ORDER if current_stages.get(s, {}).get("status") != "skipped"]

    dirty_set: set = set()

    # 1. So sánh từng key trong CONFIG_DEPENDENCIES
    for key, affected_stages in CONFIG_DEPENDENCIES.items():
        old_val = old_config.get(key)
        new_val = new_config.get(key)
        if old_val != new_val:
            for s in affected_stages:
                dirty_set.add(s)

    # 2. Kiểm tra cờ kích hoạt lại stage nếu có
    if new_config.get("run_stt") and not old_config.get("run_stt"):
        for s in ["stt", "translation", "tts", "audio_sync", "subtitle", "render"]:
            dirty_set.add(s)
    if new_config.get("run_translation") and not old_config.get("run_translation"):
        for s in ["translation", "tts", "audio_sync", "subtitle", "render"]:
            dirty_set.add(s)
    if new_config.get("run_tts") and not old_config.get("run_tts"):
        for s in ["tts", "audio_sync", "render"]:
            dirty_set.add(s)

    # 3. Kiểm tra các stage chưa hoàn thành trong pipeline hiện tại
    for s_name in CANONICAL_STAGE_ORDER:
        st = current_stages.get(s_name, {})
        if st.get("status") not in ["completed", "skipped"]:
            dirty_set.add(s_name)

    if not dirty_set:
        return []

    # Sắp xếp các stage bị dirty theo CANONICAL_STAGE_ORDER
    dirty_stages = [s for s in CANONICAL_STAGE_ORDER if s in dirty_set and current_stages.get(s, {}).get("status") != "skipped"]
    return dirty_stages


def create_initial_job_state(job_id: str) -> Dict[str, Any]:
    """
    Khởi tạo cấu trúc Job State chuẩn xác với tất cả stages ở trạng thái pending.
    """
    stages: Dict[str, Any] = {}
    for name, defn in STAGE_DEFINITIONS.items():
        stages[name] = {
            "name": name,
            "label": defn["label"],
            "status": "pending",
            "started_at": None,
            "completed_at": None,
            "duration_ms": None,
            "progress": None,
            "message": "Chờ xử lý",
            "error_code": None,
            "automatic_attempt": None,
            "max_automatic_attempts": 3,
            "is_retrying": False,
            "extra": {},
        }

    return {
        "job_id": job_id,
        "status": "uploaded",
        "current_stage": None,
        "progress": 0.0,
        "output_revision": 0,
        "config_revision": 0,
        "created_at": _iso_now(),
        "stages": stages,
        "artifacts": {},
    }


def calculate_global_progress(stages: Dict[str, Any], enabled_stage_names: Optional[List[str]] = None) -> float:
    """
    Tính Weighted Global Progress:
    - Loại bỏ hoàn toàn các stage bị 'skipped' hoặc không nằm trong enabled_stage_names khỏi mẫu số.
    - Cộng dồn trọng số các stage completed + phần đóng góp nội bộ của stage đang running.
    """
    if enabled_stage_names is not None:
        target_stages = {k: v for k, v in stages.items() if k in enabled_stage_names and v.get("status") != "skipped"}
    else:
        target_stages = {k: v for k, v in stages.items() if v.get("status") != "skipped"}

    if not target_stages:
        return 100.0

    total_weight = sum(STAGE_DEFINITIONS.get(k, {}).get("weight", 10) for k in target_stages.keys())
    if total_weight <= 0:
        return 100.0

    completed_weight = sum(
        STAGE_DEFINITIONS.get(k, {}).get("weight", 10)
        for k, v in target_stages.items()
        if v.get("status") == "completed"
    )

    running_weight_contrib = 0.0
    for k, v in target_stages.items():
        if v.get("status") == "running":
            w = STAGE_DEFINITIONS.get(k, {}).get("weight", 10)
            stage_prog = v.get("progress")
            if stage_prog is not None:
                try:
                    pct = float(stage_prog)
                    running_weight_contrib += w * (max(0.0, min(100.0, pct)) / 100.0)
                except (ValueError, TypeError):
                    pass
            break

    global_pct = ((completed_weight + running_weight_contrib) / total_weight) * 100.0
    return round(max(0.0, min(100.0, global_pct)), 1)


def save_job_info_atomic_sync(job_id: str, job_info: Dict[str, Any]) -> None:
    """
    Ghi job_info.json theo cơ chế Atomic Write (ghi file .tmp rồi os.replace)
    kết hợp retry & fallback trên Windows để ngăn chặn triệt để xung đột race condition.
    """
    paths = get_job_paths(job_id)
    if not paths:
        return

    job_file = paths["job_dir"] / "job_info.json"
    temp_file = paths["job_dir"] / f"job_info_{int(time.time()*1000)}.tmp"

    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(job_info, f, indent=2, ensure_ascii=False)

        # Retry replace on Windows in case another thread is reading
        for attempt in range(5):
            try:
                os.replace(str(temp_file), str(job_file))
                break
            except (PermissionError, OSError):
                if attempt == 4:
                    # Fallback direct write
                    with open(job_file, "w", encoding="utf-8") as f:
                        json.dump(job_info, f, indent=2, ensure_ascii=False)
                else:
                    time.sleep(0.01 * (attempt + 1))
    except Exception as e:
        logger.error(f"Lỗi atomic write job_info cho {job_id}: {e}", exc_info=True)
    finally:
        if temp_file.exists():
            try:
                temp_file.unlink(missing_ok=True)
            except Exception:
                pass


async def save_job_info_atomic(job_id: str, job_info: Dict[str, Any]) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, save_job_info_atomic_sync, job_id, job_info)


def load_job_info_sync(job_id: str) -> Optional[Dict[str, Any]]:
    paths = get_job_paths(job_id)
    if not paths:
        return None

    job_file = paths["job_dir"] / "job_info.json"
    if not job_file.exists():
        return None

    # Retry up to 3 times in case of filesystem locking on Windows
    for attempt in range(3):
        try:
            with open(job_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, PermissionError):
            time.sleep(0.02 * (attempt + 1))
    return None


async def load_job_info(job_id: str) -> Optional[Dict[str, Any]]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, load_job_info_sync, job_id)


async def start_stage(
    job_id: str,
    stage_name: str,
    message: Optional[str] = None,
    initial_progress: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Bắt đầu thực thi một stage:
    - Đặt status = 'running'
    - Ghi nhận started_at
    - Cập nhật current_stage và tính lại global progress
    - initial_progress: Nếu được cung cấp (ví dụ nạp từ checkpoint TTS 95.5%), giữ nguyên thay vì reset về 0.0.
    """
    lock = _get_job_lock(job_id)
    async with lock:
        job_info = await load_job_info(job_id) or create_initial_job_state(job_id)
        stages = job_info.setdefault("stages", {})
        st = stages.setdefault(stage_name, {
            "name": stage_name,
            "label": STAGE_DEFINITIONS.get(stage_name, {}).get("label", stage_name),
            "status": "pending",
            "started_at": None,
            "completed_at": None,
            "duration_ms": None,
            "progress": None,
            "message": "Chờ xử lý",
            "error_code": None,
            "extra": {},
        })

        st["status"] = "running"
        st["started_at"] = _iso_now()
        st["completed_at"] = None
        st["duration_ms"] = None
        if initial_progress is not None:
            st["progress"] = initial_progress
        elif st.get("progress") is not None and st.get("progress", 0.0) > 0.0:
            st["progress"] = st.get("progress")
        else:
            st["progress"] = 0.0
        st["error_code"] = None
        st["automatic_attempt"] = None
        st["is_retrying"] = False
        if message:
            st["message"] = message

        job_info["status"] = "processing"
        job_info["error"] = None
        job_info["current_stage"] = stage_name
        job_info["progress"] = calculate_global_progress(stages)
        await save_job_info_atomic(job_id, job_info)
        return job_info


async def update_stage_progress(
    job_id: str,
    stage_name: str,
    progress: Optional[float] = None,
    message: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Cập nhật tiến độ nội bộ của stage (ví dụ TTS 42/120 SpeechChunks):
    - progress: % tiến độ nội bộ (0 -> 100)
    - message: mô tả tiến độ thực tế
    """
    lock = _get_job_lock(job_id)
    async with lock:
        job_info = await load_job_info(job_id)
        if not job_info:
            return {}

        stages = job_info.setdefault("stages", {})
        if stage_name in stages:
            st = stages[stage_name]
            st["status"] = "running"
            if progress is not None:
                st["progress"] = round(float(progress), 1)
            if message is not None:
                st["message"] = message
            if extra:
                st.setdefault("extra", {}).update(extra)

            job_info["progress"] = calculate_global_progress(stages)
            await save_job_info_atomic(job_id, job_info)
        return job_info


async def update_stage_retry(
    job_id: str,
    stage_name: str,
    attempt: int,
    max_attempts: int = 3,
    message: Optional[str] = None,
    progress: Optional[float] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Cập nhật trạng thái Auto-Retry realtime của stage:
    - automatic_attempt: Lần thử lại hiện tại (1, 2, 3)
    - is_retrying: True
    - Giữ nguyên progress đã hoàn thành (không nhảy về 0%)
    - message: Thông báo thử lại (ví dụ: 'Đang tự thử lại lần 1/3...')
    """
    lock = _get_job_lock(job_id)
    async with lock:
        job_info = await load_job_info(job_id)
        if not job_info:
            return {}

        stages = job_info.setdefault("stages", {})
        if stage_name in stages:
            st = stages[stage_name]
            st["status"] = "running"
            st["automatic_attempt"] = attempt
            st["max_automatic_attempts"] = max_attempts
            st["is_retrying"] = True
            if progress is not None:
                st["progress"] = round(float(progress), 1)
            if message is not None:
                st["message"] = message
            else:
                st["message"] = f"Lỗi tạm thời. Đang tự thử lại lần {attempt}/{max_attempts}..."
            if extra:
                st.setdefault("extra", {}).update(extra)

            job_info["status"] = "processing"
            job_info["progress"] = calculate_global_progress(stages)
            await save_job_info_atomic(job_id, job_info)
        return job_info


async def complete_stage(
    job_id: str,
    stage_name: str,
    message: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Hoàn tất một stage:
    - Đặt status = 'completed'
    - Ghi nhận completed_at và tính toán duration_ms thực tế
    - Xóa trạng thái retry
    - Tính lại global progress
    """
    lock = _get_job_lock(job_id)
    async with lock:
        job_info = await load_job_info(job_id)
        if not job_info:
            return {}

        stages = job_info.setdefault("stages", {})
        st = stages.setdefault(stage_name, {})
        st["status"] = "completed"
        now_iso = _iso_now()
        st["completed_at"] = now_iso
        st["progress"] = 100.0
        st["automatic_attempt"] = None
        st["is_retrying"] = False

        if message:
            st["message"] = message

        if extra:
            st.setdefault("extra", {}).update(extra)

        # Tính duration_ms thực tế
        started_iso = st.get("started_at")
        if started_iso:
            try:
                t0 = datetime.fromisoformat(started_iso.replace("Z", "+00:00")).timestamp()
                t1 = datetime.fromisoformat(now_iso.replace("Z", "+00:00")).timestamp()
                st["duration_ms"] = max(0, int(round((t1 - t0) * 1000)))
            except Exception:
                st["duration_ms"] = 0
        else:
            st["started_at"] = now_iso
            st["duration_ms"] = 0

        job_info["progress"] = calculate_global_progress(stages)
        await save_job_info_atomic(job_id, job_info)
        return job_info


async def fail_stage(
    job_id: str,
    stage_name: str,
    error_code: str,
    message: str,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Đánh dấu stage thất bại:
    - Đặt status = 'failed'
    - Ghi nhận error_code và user-friendly message
    - Đặt job_info.status = 'failed'
    """
    lock = _get_job_lock(job_id)
    async with lock:
        job_info = await load_job_info(job_id)
        if not job_info:
            return {}

        stages = job_info.setdefault("stages", {})
        st = stages.setdefault(stage_name, {})
        st["status"] = "failed"
        st["completed_at"] = _iso_now()
        st["error_code"] = error_code
        st["message"] = message
        st["is_retrying"] = False
        if extra:
            st.setdefault("extra", {}).update(extra)

        job_info["status"] = "failed"
        job_info["error"] = message
        await save_job_info_atomic(job_id, job_info)
        return job_info


async def skip_stage(job_id: str, stage_name: str, message: Optional[str] = "Bỏ qua theo tùy chọn") -> Dict[str, Any]:
    """
    Đánh dấu stage bị bỏ qua do người dùng không chọn:
    - Đặt status = 'skipped'
    - Không tính vào mẫu số của global progress
    """
    lock = _get_job_lock(job_id)
    async with lock:
        job_info = await load_job_info(job_id)
        if not job_info:
            return {}

        stages = job_info.setdefault("stages", {})
        st = stages.setdefault(stage_name, {})
        st["status"] = "skipped"
        st["message"] = message or "Bỏ qua"
        st["started_at"] = None
        st["completed_at"] = None
        st["duration_ms"] = None
        st["progress"] = None
        st["automatic_attempt"] = None
        st["is_retrying"] = False

        job_info["progress"] = calculate_global_progress(stages)
        await save_job_info_atomic(job_id, job_info)
        return job_info


async def reset_failed_stages_for_retry(job_id: str, resume_from_failed: bool = True) -> Optional[Dict[str, Any]]:
    """
    Khôi phục trạng thái Job để thực hiện Retry theo cơ chế Strict RetryPlan:
    - Xác định failed_stage và resume_stage.
    - Giữ nguyên 100% các stage trong preserved_stages (completed, progress=100%, timestamp, duration).
    - Tái tạo initial_progress thực tế cho resume_stage từ checkpoint đĩa (không reset về 0%).
    - Đặt các stage downstream trong execution_plan sang pending.
    """
    lock = _get_job_lock(job_id)
    async with lock:
        job_info = await load_job_info(job_id)
        if not job_info:
            return None

        stages = job_info.setdefault("stages", {})
        now_iso = _iso_now()

        # 1. Tìm failed_stage đầu tiên trong CANONICAL_STAGE_ORDER
        failed_stage = None
        for name in CANONICAL_STAGE_ORDER:
            st = stages.get(name, {})
            if st.get("status") == "failed":
                failed_stage = name
                break

        if not failed_stage and job_info.get("status") == "failed":
            curr = job_info.get("current_stage")
            if curr in CANONICAL_STAGE_ORDER:
                failed_stage = curr
            else:
                for name in CANONICAL_STAGE_ORDER:
                    if stages.get(name, {}).get("status") not in ["completed", "skipped"]:
                        failed_stage = name
                        break

        if not resume_from_failed:
            failed_stage = None
            resume_stage = CANONICAL_STAGE_ORDER[0]
            resume_idx = 0
        elif not failed_stage:
            resume_stage = CANONICAL_STAGE_ORDER[0]
            resume_idx = 0
        else:
            resume_stage = failed_stage
            resume_idx = CANONICAL_STAGE_ORDER.index(resume_stage)

        preserved_stages = CANONICAL_STAGE_ORDER[:resume_idx]
        execution_plan = CANONICAL_STAGE_ORDER[resume_idx:]

        # 2. Xử lý từng stage theo RetryPlan
        job_paths = get_job_paths(job_id)

        for name in CANONICAL_STAGE_ORDER:
            st = stages.setdefault(name, {
                "name": name,
                "label": STAGE_DEFINITIONS.get(name, {}).get("label", name),
                "status": "pending",
                "progress": 0.0,
            })

            if not resume_from_failed:
                st["status"] = "pending"
                st["message"] = "Chờ xử lý (Chạy lại)"
                st["error_code"] = None
                st["started_at"] = None
                st["completed_at"] = None
                st["duration_ms"] = None
                st["progress"] = 0.0
                st["automatic_attempt"] = None
                st["is_retrying"] = False
            elif name in preserved_stages:
                # BẢO TOÀN NGUYÊN VẸN 100% UPSTREAM STAGES
                st["status"] = "completed"
                st["error_code"] = None
                st["automatic_attempt"] = None
                st["is_retrying"] = False
                if st.get("progress") is None or st.get("progress", 0.0) < 100.0:
                    st["progress"] = 100.0
            elif name == resume_stage:
                # Stage phục hồi: Khôi phục tiến độ thực từ checkpoint
                initial_pct = 0.0
                initial_msg = "Đang khởi động lại từ đoạn bị lỗi..."

                if resume_stage == "tts" and job_paths:
                    tts_dir = job_paths.get("tts_dir")
                    if tts_dir and tts_dir.exists():
                        # Xóa file 0-byte hoặc < MIN_VALID_AUDIO_BYTES (Invariant 2)
                        for mp3_f in tts_dir.glob("segment_*.mp3"):
                            try:
                                if mp3_f.stat().st_size < MIN_VALID_AUDIO_BYTES:
                                    mp3_f.unlink(missing_ok=True)
                            except Exception:
                                pass

                        mp3_files = [f for f in tts_dir.glob("segment_*.mp3") if f.stat().st_size >= MIN_VALID_AUDIO_BYTES]
                        chk_file = tts_dir / "tts_chunks_state.json"
                        trans_file = job_paths.get("transcript_dir", Path()) / "translated_transcript.json"
                        orig_trans_file = job_paths.get("transcript_dir", Path()) / "transcript.json"

                        total_chunks = len(job_info.get("segments", []))
                        if total_chunks == 0 and trans_file.exists():
                            try:
                                with open(trans_file, "r", encoding="utf-8") as tf:
                                    td = json.load(tf)
                                    total_chunks = len(td.get("speech_chunks") or td.get("segments", []))
                            except Exception:
                                pass
                        if total_chunks == 0 and orig_trans_file.exists():
                            try:
                                with open(orig_trans_file, "r", encoding="utf-8") as of:
                                    od = json.load(of)
                                    total_chunks = len(od.get("speech_chunks") or od.get("segments", []))
                            except Exception:
                                pass
                        if chk_file.exists():
                            try:
                                with open(chk_file, "r", encoding="utf-8") as cf:
                                    chk_data = json.load(cf)
                                    total_chunks = max(total_chunks, len(chk_data))
                            except Exception:
                                pass

                        completed_chunks = len(mp3_files)
                        if total_chunks > 0:
                            initial_pct = round((completed_chunks / max(1, total_chunks)) * 100.0, 1)
                            initial_msg = (
                                f"Đang tiếp tục tổng hợp {completed_chunks}/{total_chunks} SpeechChunks ({initial_pct}%)"
                                if completed_chunks > 0
                                else "Đang tổng hợp giọng đọc AI..."
                            )
                        else:
                            initial_pct = st.get("progress", 0.0) or 0.0

                elif resume_stage == "translation" and job_paths:
                    trans_file = job_paths.get("transcript_dir", Path()) / "translated_transcript.json"
                    if trans_file.exists():
                        try:
                            with open(trans_file, "r", encoding="utf-8") as tf:
                                t_data = json.load(tf)
                                t_chunks = t_data.get("speech_chunks") or t_data.get("segments", [])
                                done_t = len([c for c in t_chunks if (c.get("translated_text") or "").strip() != (c.get("original_text") or "").strip()])
                                total_t = len(t_chunks)
                                if total_t > 0:
                                    initial_pct = round((done_t / max(1, total_t)) * 100.0, 1)
                                    initial_msg = f"Đang tiếp tục dịch thuật ({done_t}/{total_t} câu, {initial_pct}%)..."
                        except Exception:
                            initial_pct = st.get("progress", 0.0) or 0.0
                else:
                    initial_pct = st.get("progress", 0.0) or 0.0

                st["status"] = "running"
                st["message"] = initial_msg
                st["error_code"] = None
                st["started_at"] = now_iso
                st["completed_at"] = None
                st["duration_ms"] = None
                st["progress"] = initial_pct
                st["automatic_attempt"] = None
                st["is_retrying"] = False
            else:
                # Downstream stages trong execution_plan
                st["status"] = "pending"
                st["message"] = "Chờ xử lý (Thử lại)"
                st["error_code"] = None
                st["started_at"] = None
                st["completed_at"] = None
                st["duration_ms"] = None
                st["progress"] = 0.0
                st["automatic_attempt"] = None
                st["is_retrying"] = False

        retry_plan = {
            "mode": "resume" if resume_from_failed else "rerun_all",
            "failed_stage": failed_stage,
            "resume_stage": resume_stage,
            "resume_index": resume_idx,
            "retry_scope": "failed_items" if (resume_from_failed and resume_stage in ["tts", "translation"]) else "stage",
            "preserve_upstream": bool(preserved_stages),
            "preserved_stages": preserved_stages,
            "execution_plan": execution_plan,
            "initial_progress": stages.get(resume_stage, {}).get("progress", 0.0) if resume_stage else 0.0,
        }

        job_info["status"] = "processing"
        job_info["error"] = None
        job_info["current_stage"] = resume_stage
        job_info["retry_plan"] = retry_plan
        job_info["retry_count"] = job_info.get("retry_count", 0) + 1
        job_info["last_retry_at"] = now_iso
        job_info["progress"] = calculate_global_progress(stages)
        await save_job_info_atomic(job_id, job_info)
        return job_info


async def prepare_job_for_reprocess(
    job_id: str,
    new_config: Dict[str, Any],
    dirty_stages: List[str],
) -> Optional[Dict[str, Any]]:
    """
    Chuẩn bị trạng thái Job để xử lý lại (Reprocess) khi cấu hình thay đổi:
    - Xác định earliest_dirty_stage từ CANONICAL_STAGE_ORDER.
    - Bảo toàn 100% upstream stages (status='completed', progress=100%, timestamps).
    - Invalidate các downstream stages dirty: đặt status='pending', message='Chờ xử lý (Cấu hình thay đổi)', progress=0.0.
    - Đánh dấu artifact final_video cũ: current=False, reprocessing=True.
    - Cập nhật config_snapshot và tăng config_revision.
    """
    lock = _get_job_lock(job_id)
    async with lock:
        job_info = await load_job_info(job_id)
        if not job_info:
            return None

        stages = job_info.setdefault("stages", {})

        if not dirty_stages:
            return job_info

        earliest_dirty_stage = None
        for name in CANONICAL_STAGE_ORDER:
            if name in dirty_stages:
                earliest_dirty_stage = name
                break

        if not earliest_dirty_stage:
            earliest_dirty_stage = CANONICAL_STAGE_ORDER[0]

        earliest_idx = CANONICAL_STAGE_ORDER.index(earliest_dirty_stage)
        preserved_stages = CANONICAL_STAGE_ORDER[:earliest_idx]
        execution_plan = CANONICAL_STAGE_ORDER[earliest_idx:]

        for name in CANONICAL_STAGE_ORDER:
            st = stages.setdefault(name, {
                "name": name,
                "label": STAGE_DEFINITIONS.get(name, {}).get("label", name),
                "status": "pending",
                "progress": 0.0,
            })

            if name in preserved_stages:
                # BẢO TOÀN NGUYÊN VẸN UPSTREAM STAGES
                st["status"] = "completed"
                st["error_code"] = None
                st["automatic_attempt"] = None
                st["is_retrying"] = False
                if st.get("progress") is None or st.get("progress", 0.0) < 100.0:
                    st["progress"] = 100.0
            else:
                # DOWNSTREAM DIRTY STAGES
                st["status"] = "pending"
                st["message"] = "Chờ xử lý (Cấu hình thay đổi)" if name == earliest_dirty_stage else "Chờ xử lý"
                st["error_code"] = None
                st["started_at"] = None
                st["completed_at"] = None
                st["duration_ms"] = None
                st["progress"] = 0.0
                st["automatic_attempt"] = None
                st["is_retrying"] = False

        # Invalidate artifacts
        artifacts = job_info.setdefault("artifacts", {})
        if "final_video" in artifacts:
            artifacts["final_video"]["current"] = False
            artifacts["final_video"]["reprocessing"] = True
        if "video" in job_info and isinstance(job_info["video"], dict):
            job_info["video"]["current"] = False
            job_info["video"]["reprocessing"] = True

        reprocess_plan = {
            "mode": "reprocess",
            "earliest_dirty_stage": earliest_dirty_stage,
            "dirty_stages": dirty_stages,
            "resume_stage": earliest_dirty_stage,
            "resume_index": earliest_idx,
            "preserve_upstream": bool(preserved_stages),
            "preserved_stages": preserved_stages,
            "execution_plan": execution_plan,
        }

        job_info["status"] = "processing"
        job_info["error"] = None
        job_info["current_stage"] = earliest_dirty_stage
        job_info["retry_plan"] = reprocess_plan
        job_info["config_snapshot"] = new_config
        job_info["config_revision"] = job_info.get("config_revision", 0) + 1
        job_info["progress"] = calculate_global_progress(stages)
        await save_job_info_atomic(job_id, job_info)
        return job_info


def get_all_jobs_summary_sync() -> List[Dict[str, Any]]:
    """
    Quét thư mục data/jobs/ và trả về danh sách tóm tắt nhẹ của toàn bộ Job History:
    - Không load các file transcript/TTS/audio lớn vào RAM.
    - Sắp xếp theo created_at giảm dần (mới nhất lên đầu).
    """
    from backend.config import JOBS_DIR
    if not JOBS_DIR.exists():
        return []

    summaries = []
    for item in JOBS_DIR.iterdir():
        if item.is_dir():
            job_file = item / "job_info.json"
            if job_file.exists():
                try:
                    with open(job_file, "r", encoding="utf-8") as f:
                        j_data = json.load(f)

                    j_id = j_data.get("job_id", item.name)
                    v_info = j_data.get("video_info", {})
                    v_obj = j_data.get("video", {})
                    cfg = j_data.get("config_snapshot", {})
                    artifacts = j_data.get("artifacts", {})

                    filename = v_info.get("filename") or v_obj.get("filename") or cfg.get("filename") or "video.mp4"
                    dur = v_info.get("duration") or v_obj.get("duration") or 0.0
                    dur_fmt = v_info.get("duration_formatted") or v_obj.get("duration_formatted") or "00:00"

                    has_final_video = bool(
                        artifacts.get("final_video", {}).get("available")
                        or (item / "output" / "final_dubbed.mp4").exists()
                    )

                    summaries.append({
                        "job_id": j_id,
                        "filename": filename,
                        "created_at": j_data.get("created_at", _iso_now()),
                        "status": j_data.get("status", "uploaded"),
                        "progress": j_data.get("progress", 0.0),
                        "duration": dur,
                        "duration_formatted": dur_fmt,
                        "target_language": cfg.get("target_language") or artifacts.get("translation", {}).get("target_language") or "vi",
                        "voice_id": cfg.get("voice_id") or "vi-VN-NamMinhNeural",
                        "final_video_available": has_final_video,
                        "error": j_data.get("error"),
                    })
                except Exception as e:
                    logger.warning(f"Lỗi đọc summary cho job {item.name}: {e}")

    # Sắp xếp mới nhất trước
    return sorted(summaries, key=lambda x: str(x.get("created_at", "")), reverse=True)


async def get_all_jobs_summary() -> List[Dict[str, Any]]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, get_all_jobs_summary_sync)


def delete_job_sync(job_id: str) -> bool:
    """
    Xóa thư mục dữ liệu của Job an toàn trên filesystem.
    """
    import shutil
    paths = get_job_paths(job_id)
    if paths and paths["job_dir"].exists():
        try:
            shutil.rmtree(str(paths["job_dir"]))
            return True
        except Exception as e:
            logger.error(f"Lỗi khi xóa job {job_id}: {e}")
            return False
    return False


async def delete_job(job_id: str) -> bool:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, delete_job_sync, job_id)


def recover_stale_running_jobs_sync(jobs_dir: Optional[Path] = None) -> List[str]:
    """
    Quét và thu hồi các zombie jobs khi server khởi động dựa trên RUNTIME_INSTANCE_ID (Invariant 4):
    - Kiểm tra các job có status == "processing" hoặc stage running nhưng worker_instance_id != RUNTIME_INSTANCE_ID.
    - Reconcile đĩa: Xóa các file 0-byte trong tts_dir, đếm chính xác số file MP3 hợp lệ (>= MIN_VALID_AUDIO_BYTES).
    - Cập nhật trạng thái: job.status = "failed", stage.status = "failed",
      error_code = "TASK_INTERRUPTED_SERVER_RESTART",
      error = "Tiến trình bị gián đoạn do máy chủ khởi động lại. Bấm 'Thử lại' để tiếp tục từ vị trí đã dừng.".
    - Tái dựng progress = (valid_completed / total) * 100.0%.
    """
    from backend.config import JOBS_DIR as CONFIG_JOBS_DIR, RUNTIME_INSTANCE_ID, MIN_VALID_AUDIO_BYTES
    target_jobs_dir = jobs_dir or CONFIG_JOBS_DIR
    if not target_jobs_dir.exists():
        return []

    recovered_job_ids = []
    for item in target_jobs_dir.iterdir():
        if not item.is_dir():
            continue
        job_file = item / "job_info.json"
        if not job_file.exists() or job_file.stat().st_size == 0:
            continue

        job_id = item.name
        try:
            with open(job_file, "r", encoding="utf-8") as f:
                job_info = json.load(f)

            if not job_info or not isinstance(job_info, dict):
                continue

            status = job_info.get("status")
            stages = job_info.get("stages", {})
            has_running_stage = any(s.get("status") == "running" for s in stages.values())
            worker_id = job_info.get("worker_instance_id")

            is_zombie = (status == "processing" or has_running_stage) and (worker_id != RUNTIME_INSTANCE_ID)

            if is_zombie:
                logger.warning(
                    f"[WATCHDOG] Phát hiện Zombie Job '{job_id}' (worker_id={worker_id} != {RUNTIME_INSTANCE_ID}). "
                    f"Tiến hành thu hồi và reconcile trạng thái..."
                )

                # 1. Reconcile tts_dir: Xóa file rỗng / corrupted
                tts_dir = item / "tts"
                valid_mp3_count = 0
                if tts_dir.exists():
                    for mp3_f in tts_dir.glob("segment_*.mp3"):
                        try:
                            if mp3_f.stat().st_size < MIN_VALID_AUDIO_BYTES:
                                mp3_f.unlink(missing_ok=True)
                                logger.info(f"[WATCHDOG] Đã xóa file audio rỗng/hỏng: {mp3_f.name}")
                            else:
                                valid_mp3_count += 1
                        except Exception:
                            pass

                # Đọc tổng số chunks từ translated_transcript hoặc transcript hoặc segments
                total_chunks = len(job_info.get("segments", []))
                trans_file = item / "transcripts" / "translated_transcript.json"
                orig_trans_file = item / "transcripts" / "transcript.json"
                chk_file = tts_dir / "tts_chunks_state.json"

                if total_chunks == 0 and trans_file.exists():
                    try:
                        with open(trans_file, "r", encoding="utf-8") as tf:
                            td = json.load(tf)
                            total_chunks = len(td.get("speech_chunks") or td.get("segments", []))
                    except Exception:
                        pass
                if total_chunks == 0 and orig_trans_file.exists():
                    try:
                        with open(orig_trans_file, "r", encoding="utf-8") as of:
                            od = json.load(of)
                            total_chunks = len(od.get("speech_chunks") or od.get("segments", []))
                    except Exception:
                        pass
                if chk_file.exists():
                    try:
                        with open(chk_file, "r", encoding="utf-8") as cf:
                            cd = json.load(cf)
                            total_chunks = max(total_chunks, len(cd))
                    except Exception:
                        pass

                # 2. Cập nhật các stage đang running sang failed
                restart_msg = "Tiến trình bị gián đoạn do máy chủ khởi động lại. Bấm 'Thử lại' để tiếp tục từ vị trí đã dừng."
                for s_name, s_data in stages.items():
                    if s_data.get("status") == "running":
                        s_data["status"] = "failed"
                        s_data["error_code"] = "TASK_INTERRUPTED_SERVER_RESTART"
                        s_data["message"] = restart_msg
                        s_data["completed_at"] = _iso_now()
                        s_data["is_retrying"] = False
                        if s_name == "tts" and total_chunks > 0:
                            tts_pct = round((valid_mp3_count / max(1, total_chunks)) * 100.0, 1)
                            s_data["progress"] = tts_pct
                            s_data.setdefault("extra", {})["completed_chunks"] = valid_mp3_count
                            s_data.setdefault("extra", {})["total_chunks"] = total_chunks

                job_info["status"] = "failed"
                job_info["error"] = restart_msg
                job_info["progress"] = calculate_global_progress(stages)

                temp_file = item / f"job_info_{int(time.time()*1000)}.tmp"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(job_info, f, indent=2, ensure_ascii=False)
                for attempt in range(5):
                    try:
                        os.replace(str(temp_file), str(job_file))
                        break
                    except (PermissionError, OSError):
                        if attempt == 4:
                            with open(job_file, "w", encoding="utf-8") as f:
                                json.dump(job_info, f, indent=2, ensure_ascii=False)
                        else:
                            time.sleep(0.01 * (attempt + 1))
                if temp_file.exists():
                    try:
                        temp_file.unlink(missing_ok=True)
                    except Exception:
                        pass

                recovered_job_ids.append(job_id)
                logger.info(f"[WATCHDOG] Đã thu hồi thành công Job '{job_id}' (Progress: {job_info.get('progress')}%)")

        except Exception as e:
            logger.error(f"[WATCHDOG] Lỗi khi reconcile job {job_id}: {e}", exc_info=True)

    return recovered_job_ids


async def recover_stale_running_jobs(jobs_dir: Optional[Path] = None) -> List[str]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, recover_stale_running_jobs_sync, jobs_dir)

