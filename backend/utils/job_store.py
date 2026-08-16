import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.utils.file_utils import get_job_paths

logger = logging.getLogger("job_store")

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

_JOB_LOCKS: Dict[str, asyncio.Lock] = {}


def _get_job_lock(job_id: str) -> asyncio.Lock:
    if job_id not in _JOB_LOCKS:
        _JOB_LOCKS[job_id] = asyncio.Lock()
    return _JOB_LOCKS[job_id]


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
            "extra": {},
        }

    return {
        "job_id": job_id,
        "status": "uploaded",
        "current_stage": None,
        "progress": 0.0,
        "created_at": _iso_now(),
        "stages": stages,
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


async def start_stage(job_id: str, stage_name: str, message: Optional[str] = None) -> Dict[str, Any]:
    """
    Bắt đầu thực thi một stage:
    - Đặt status = 'running'
    - Ghi nhận started_at
    - Cập nhật current_stage và tính lại global progress
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
        st["progress"] = 0.0
        st["error_code"] = None
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

        job_info["progress"] = calculate_global_progress(stages)
        await save_job_info_atomic(job_id, job_info)
        return job_info


async def reset_failed_stages_for_retry(job_id: str, resume_from_failed: bool = True) -> Optional[Dict[str, Any]]:
    """
    Khôi phục trạng thái Job để thực hiện Retry:
    - Nếu resume_from_failed=True: Giữ nguyên các stage đã completed trước đó, chỉ reset stage bị failed (và các stage sau nó) về pending.
    - Nếu resume_from_failed=False: Reset toàn bộ các stage về pending (chạy lại từ đầu).
    """
    lock = _get_job_lock(job_id)
    async with lock:
        job_info = await load_job_info(job_id)
        if not job_info:
            return None

        stages = job_info.setdefault("stages", {})
        found_failure = False

        for name in list(STAGE_DEFINITIONS.keys()):
            if name in ["upload", "metadata"]:
                continue

            st = stages.setdefault(name, {})
            current_st_status = st.get("status")

            if not resume_from_failed:
                st["status"] = "pending"
                st["message"] = "Chờ xử lý (Chạy lại)"
                st["error_code"] = None
                st["started_at"] = None
                st["completed_at"] = None
                st["duration_ms"] = None
                st["progress"] = 0.0
            elif current_st_status == "failed" or found_failure:
                found_failure = True
                st["status"] = "pending"
                st["message"] = "Chờ xử lý (Thử lại)"
                st["error_code"] = None
                st["started_at"] = None
                st["completed_at"] = None
                st["duration_ms"] = None
                st["progress"] = 0.0

        job_info["status"] = "processing"
        job_info["error"] = None
        job_info["retry_count"] = job_info.get("retry_count", 0) + 1
        job_info["last_retry_at"] = _iso_now()
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
