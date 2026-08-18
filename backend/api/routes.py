import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import aiofiles
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

from backend.config import (
    ALLOWED_VIDEO_EXTENSIONS,
    FINAL_AUDIO_SAMPLE_RATE,
    MAX_UPLOAD_SIZE_BYTES,
    RUNTIME_INSTANCE_ID,
    WHISPER_AUDIO_SAMPLE_RATE,
    WHISPER_DEFAULT_MODEL,
)
from backend.services.audio_sync_service import (
    AudioSyncError,
    normalize_audio_sync_result,
    reconstruct_tts_segments_from_disk,
    sync_and_combine_voice_track,
    validate_audio_sync_segments,
)
from backend.services.render_service import render_final_video
from backend.services.speech_chunk_service import build_speech_chunks_from_stt
from backend.services.speech_continuity_service import analyze_speech_continuity
from backend.services.stt_service import transcribe_audio
from backend.services.subtitle_service import (
    ensure_subtitle_artifact,
    ensure_translated_srt_artifact,
    save_ass_file,
    save_srt_file,
)
from backend.services.translation_service import translate_transcript_segments
from backend.services.tts_service import (
    generate_all_segments,
    generate_speech_for_text,
    get_available_voices,
    get_voice_catalog,
    get_voice_preset_metadata,
    resolve_effective_tts_speed,
)
from backend.services.validation_service import compute_pipeline_metrics
from backend.services.video_service import extract_dual_audio, get_video_info
from backend.utils.ffmpeg_utils import check_ffmpeg_installed, probe_media_file
from backend.utils.file_utils import (
    create_job_directory,
    format_file_size,
    get_job_paths,
    is_allowed_video_file,
    sanitize_filename,
)
from backend.utils.job_store import (
    CANONICAL_STAGE_ORDER,
    compute_dirty_stages,
    create_initial_job_state,
    delete_job,
    get_all_jobs_summary,
    load_job_info,
    prepare_job_for_reprocess,
    register_active_task,
    reset_failed_stages_for_retry,
    save_job_info_atomic,
    start_stage,
    unregister_active_task,
    update_stage_progress,
    update_stage_retry,
    complete_stage,
    fail_stage,
    skip_stage,
)
from backend.utils.retry_utils import (
    execute_with_auto_retry,
    is_fatal_api_key_error,
    is_recoverable_error,
)
from backend.utils.batch_store import (
    create_batch,
    load_batch_info,
    update_batch_state,
    calculate_batch_progress,
)

# Schemas Pydantic
class MaskRegionModel(BaseModel):
    id: str
    x: float = 0.10          # Normalized 0.0 - 1.0 (Top-Left x)
    y: float = 0.75          # Normalized 0.0 - 1.0 (Top-Left y)
    width: float = 0.80      # Normalized 0.0 - 1.0
    height: float = 0.15     # Normalized 0.0 - 1.0
    type: str = "blur"       # "blur" | "solid"
    blur_strength: int = 15  # 1 - 30
    color: str = "#000000"
    opacity: float = 0.85
    enabled: bool = True
    locked: bool = False

class SubtitleStyleModel(BaseModel):
    font_family: str = "Arial"
    font_size: int = 36
    primary_color: str = "#FFFFFF"
    outline_color: str = "#000000"
    outline_width: float = 2.5
    alignment: str = "bottom_center"
    margin_v: int = 60
    position_x: float = 0.50  # Normalized Center X (0.0 - 1.0)
    position_y: float = 0.88  # Normalized Center Y (0.0 - 1.0)
    width: float = 0.70       # Normalized Bounding Box Width (0.05 - 1.0)
    height: float = 0.15      # Normalized Bounding Box Height (0.05 - 1.0)
    box_x: Optional[float] = None
    box_y: Optional[float] = None
    bold: bool = True
    shadow: float = 1.0

class GeminiKeyRequest(BaseModel):
    api_key: str

class STTRequest(BaseModel):
    model: str = WHISPER_DEFAULT_MODEL
    language: Optional[str] = None

class TranslateRequest(BaseModel):
    target_language: str = "vi"
    source_language: Optional[str] = "auto"
    api_key: Optional[str] = None
    translation_style: Optional[str] = "standard_dubbing"

class VoicePreviewRequest(BaseModel):
    text: str = "Một bí mật kinh hoàng vừa được hé lộ, và đây là điều mà không ai có thể ngờ tới!"
    voice: str = "vi-VN-HoaiMyNeural_tiktok_review"
    speed_rate: str = "+0%"

class DubAndRenderRequest(BaseModel):
    voice: str = "vi-VN-HoaiMyNeural_tiktok_review"
    speed_rate: str = "+0%"
    keep_background_audio: bool = True
    background_volume: float = 0.15
    voice_volume: float = 1.0
    burn_subtitles: bool = False
    subtitle_style: Optional[SubtitleStyleModel] = None
    mask_regions: Optional[List[MaskRegionModel]] = None

class PipelineProcessRequest(BaseModel):
    run_stt: bool = True
    run_translation: bool = True
    run_tts: bool = True
    create_subtitle: bool = True
    subtitle_enabled: bool = True
    subtitle_mode: str = "burn"  # "burn" | "external" | "none"
    render_video: bool = True
    source_language: Optional[str] = "auto"
    target_language: str = "vi"
    translation_style: Optional[str] = "movie_review_spoken_vi"
    voice_id: str = "vi-VN-NamMinhNeural_tiktok_review"
    speed_rate: Optional[str] = "+15%"
    pitch: Optional[str] = "+0Hz"
    voice_volume: float = 1.2
    background_volume: float = 0.15
    keep_background_audio: bool = True
    burn_subtitles: bool = False
    output_resolution: str = "1080p"
    output_format: str = "mp4"
    whisper_model: str = "small"
    api_key: Optional[str] = None
    subtitle_style: Optional[SubtitleStyleModel] = None
    mask_regions: Optional[List[MaskRegionModel]] = None

class RetryRequest(BaseModel):
    resume_from_failed: bool = True
    pipeline_config: Optional[PipelineProcessRequest] = None


VALID_WHISPER_MODELS = {"tiny", "base", "small", "medium", "large-v3"}

logger = logging.getLogger("api_routes")
router = APIRouter(prefix="/api", tags=["API"])


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Kiểm tra trạng thái máy chủ và công cụ FFmpeg.
    """
    ffmpeg_ok, ffmpeg_msg = check_ffmpeg_installed()
    return {
        "status": "healthy" if ffmpeg_ok else "warning",
        "ffmpeg_installed": ffmpeg_ok,
        "message": ffmpeg_msg,
        "supported_extensions": list(ALLOWED_VIDEO_EXTENSIONS),
        "max_upload_size_mb": MAX_UPLOAD_SIZE_BYTES // (1024 * 1024),
        "final_audio_standard": f"{FINAL_AUDIO_SAMPLE_RATE} Hz Stereo",
    }


@router.get("/settings/gemini-status")
async def get_gemini_status() -> Dict[str, Any]:
    """
    Tra cứu trạng thái cấu hình Gemini API (KHÔNG bao giờ trả về raw key).
    """
    from backend.utils.credential_store import is_gemini_configured_sync, get_gemini_api_key_sync
    from backend.config import GEMINI_API_KEY
    is_conf = is_gemini_configured_sync()
    source = "env" if (GEMINI_API_KEY and GEMINI_API_KEY.strip()) else ("saved_credential" if is_conf else "none")
    return {
        "configured": is_conf,
        "status": "ACTIVE" if is_conf else "NOT_CONFIGURED",
        "source": source,
    }


@router.post("/settings/gemini-key")
async def save_gemini_key(req: GeminiKeyRequest) -> Dict[str, Any]:
    """
    Kiểm tra tính hợp lệ của key và lưu trữ bảo mật bằng mã hóa AES-GCM cục bộ.
    """
    from backend.utils.credential_store import save_gemini_api_key_sync
    key = req.api_key.strip()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gemini API Key không được để trống.",
        )

    # Validate key qua Google Generative Language API
    import httpx
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={key}")
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"INVALID_GEMINI_API_KEY: Khóa API không hợp lệ hoặc đã bị khóa (Mã lỗi: {resp.status_code}).",
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Lưu ý khi kiểm tra mạng Gemini API: {e}")
        if not key.startswith("AIza"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="INVALID_GEMINI_API_KEY: Định dạng khóa Gemini API không hợp lệ (phải bắt đầu bằng 'AIza').",
            )

    saved = save_gemini_api_key_sync(key)
    if not saved:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể mã hóa và lưu trữ khóa API vào bộ nhớ bảo mật.",
        )

    return {
        "success": True,
        "configured": True,
        "status": "ACTIVE",
        "message": "Đã lưu trữ an toàn và kích hoạt Gemini API Key thành công.",
    }


@router.delete("/settings/gemini-key")
async def delete_gemini_key() -> Dict[str, Any]:
    """
    Xóa khóa Gemini API khỏi bộ nhớ bảo mật.
    """
    from backend.utils.credential_store import delete_gemini_api_key_sync
    delete_gemini_api_key_sync()
    return {
        "success": True,
        "configured": False,
        "message": "Đã xóa Gemini API Key khỏi hệ thống.",
    }


async def _handle_single_video_upload(file: UploadFile) -> Dict[str, Any]:
    """
    Helper xử lý tải lên 1 video và trích xuất thông số metadata.
    """
    original_filename = file.filename or "video.mp4"
    if not is_allowed_video_file(original_filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Định dạng file '{original_filename}' không được hỗ trợ. "
                f"Vui lòng tải lên file thuộc các định dạng: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
            ),
        )

    clean_filename = sanitize_filename(original_filename)
    job_paths = create_job_directory()
    job_id = job_paths["job_id"]
    input_video_path = job_paths["input_dir"] / clean_filename

    job_info = create_initial_job_state(job_id)
    job_info["original_filename"] = original_filename
    job_info["clean_filename"] = clean_filename
    await save_job_info_atomic(job_id, job_info)

    await start_stage(job_id, "upload", "Đang lưu file video tải lên...")
    total_size = 0
    chunk_size = 1024 * 1024  # 1MB
    try:
        async with aiofiles.open(input_video_path, "wb") as out_file:
            while chunk := await file.read(chunk_size):
                total_size += len(chunk)
                if total_size > MAX_UPLOAD_SIZE_BYTES:
                    if input_video_path.exists():
                        input_video_path.unlink()
                    await fail_stage(job_id, "upload", "FILE_TOO_LARGE", f"Kích thước file vượt quá giới hạn ({format_file_size(MAX_UPLOAD_SIZE_BYTES)}).")
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Kích thước file vượt quá giới hạn ({format_file_size(MAX_UPLOAD_SIZE_BYTES)}).",
                    )
                await out_file.write(chunk)
            await out_file.flush()
        await complete_stage(job_id, "upload", f"Tải lên video thành công ({format_file_size(total_size)})", extra={"file_size": total_size})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi khi lưu file upload {original_filename}: {e}", exc_info=True)
        await fail_stage(job_id, "upload", "UPLOAD_FAILED", f"Lỗi khi lưu video: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lưu video: {str(e)}",
        )

    await start_stage(job_id, "metadata", "Đang phân tích thông số video qua ffprobe...")
    try:
        video_info = await get_video_info(input_video_path)
        if not video_info.get("has_audio"):
            await fail_stage(job_id, "metadata", "NO_AUDIO_STREAM", "Video không chứa âm thanh. Vui lòng chọn video có tiếng để dịch.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Video '{original_filename}' không chứa âm thanh. Vui lòng chọn video có tiếng để dịch.",
            )
        await complete_stage(job_id, "metadata", f"{video_info.get('resolution')} | {video_info.get('duration_formatted')} | {video_info.get('fps', 30)}fps", extra={"video_info": video_info})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi phân tích video {original_filename}: {e}", exc_info=True)
        await fail_stage(job_id, "metadata", "PROBE_FAILED", f"File tải lên không hợp lệ: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File tải lên không hợp lệ: {str(e)}",
        )

    job_info = await load_job_info(job_id) or job_info
    job_info["status"] = "uploaded"
    job_info["video_info"] = video_info
    await save_job_info_atomic(job_id, job_info)

    return {
        "success": True,
        "message": "Tải video lên thành công. Sẵn sàng cấu hình và xử lý.",
        "job_id": job_id,
        "status": "uploaded",
        "progress": job_info.get("progress", 0.0),
        "stages": job_info.get("stages", {}),
        "video": {
            "filename": clean_filename,
            "duration": video_info.get("duration"),
            "duration_formatted": video_info.get("duration_formatted"),
            "size": format_file_size(video_info.get("size_bytes", 0)),
            "resolution": video_info.get("resolution"),
            "preview_url": f"/api/jobs/{job_id}/video",
        },
    }


@router.post("/upload")
@router.post("/jobs/upload")
async def upload_video(file: UploadFile = File(...)) -> Dict[str, Any]:
    return await _handle_single_video_upload(file)


@router.get("/jobs/{job_id}")
async def get_job_details(job_id: str) -> Dict[str, Any]:
    """
    Lấy thông tin chi tiết trạng thái của Job (Single Source of Truth cho Frontend Polling & F5 Refresh).
    Tự động nạp các artifacts (segments, translation, final_video, srt) để frontend luôn có đầy đủ dữ liệu.
    """
    job_paths = get_job_paths(job_id)
    if not job_paths:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy Job có ID '{job_id}'.",
        )

    job_info = await load_job_info(job_id)
    if not job_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thông tin Job không tồn tại.",
        )

    artifacts = job_info.setdefault("artifacts", {})

    # 1. Nạp segments từ translated_transcript.json hoặc transcript.json
    trans_file = job_paths["transcript_dir"] / "translated_transcript.json"
    stt_file = job_paths["transcript_dir"] / "transcript.json"
    srt_file = job_paths["subtitles_dir"] / "translated.srt"

    if trans_file.exists():
        try:
            async with aiofiles.open(trans_file, "r", encoding="utf-8") as tf:
                t_data = json.loads(await tf.read())
                chunks = t_data.get("speech_chunks") or t_data.get("segments", [])
                job_info["segments"] = chunks
                artifacts["translation"] = {
                    "available": True,
                    "count": len(chunks),
                    "target_language": t_data.get("target_language", "vi"),
                    "translation_style": t_data.get("translation_style", "standard_dubbing"),
                }
                artifacts["translated_subtitle"] = {
                    "available": True,
                    "path": str(srt_file),
                    "format": "srt",
                    "count": len(chunks),
                }
        except Exception as e:
            logger.warning(f"Lỗi nạp translated_transcript.json cho job {job_id}: {e}")
    elif stt_file.exists() and not job_info.get("segments"):
        try:
            async with aiofiles.open(stt_file, "r", encoding="utf-8") as sf:
                s_data = json.loads(await sf.read())
                chunks = s_data.get("speech_chunks") or s_data.get("segments", [])
                job_info["segments"] = chunks
        except Exception as e:
            logger.warning(f"Lỗi nạp transcript.json cho job {job_id}: {e}")

    # 2. Nạp artifact và video object cho final_video nếu render hoàn tất
    output_mp4 = job_paths["output_dir"] / "final_dubbed.mp4"
    render_st = job_info.get("stages", {}).get("render", {})
    is_rendered = render_st.get("status") == "completed" and output_mp4.exists() and output_mp4.stat().st_size > 0
    is_reprocessing = (job_info.get("status") == "processing" or render_st.get("status") in ["running", "pending"]) and artifacts.get("final_video", {}).get("available")
    out_rev = job_info.get("output_revision", 1 if is_rendered else 0)

    has_subtitles = (srt_file.exists() and srt_file.stat().st_size > 0) or trans_file.exists()

    if is_rendered:
        render_res = job_info.get("render_result", {})
        file_size = output_mp4.stat().st_size
        final_video_meta = {
            "available": True,
            "current": True,
            "reprocessing": False,
            "revision": out_rev,
            "filename": output_mp4.name,
            "duration": render_res.get("duration"),
            "duration_formatted": render_res.get("duration_formatted"),
            "size": format_file_size(render_res.get("size_bytes", file_size)),
            "size_bytes": render_res.get("size_bytes", file_size),
            "resolution": render_res.get("resolution"),
            "video_url": f"/api/jobs/{job_id}/result/video?v={out_rev}",
            "download_video_url": f"/api/jobs/{job_id}/download/video?v={out_rev}",
            "download_srt_url": f"/api/jobs/{job_id}/download/subtitle?v={out_rev}" if has_subtitles else None,
            "video_codec": "h264",
            "audio_codec": "aac",
            "audio_sample_rate": 48000,
        }
        job_info["video"] = final_video_meta
        artifacts["final_video"] = final_video_meta
    elif is_reprocessing:
        if "final_video" in artifacts:
            artifacts["final_video"]["current"] = False
            artifacts["final_video"]["reprocessing"] = True
        if "video" in job_info and isinstance(job_info["video"], dict):
            job_info["video"]["current"] = False
            job_info["video"]["reprocessing"] = True

    return job_info


@router.get("/jobs")
async def list_jobs() -> Dict[str, Any]:
    """
    Lấy danh sách tóm tắt nhẹ của tất cả các Job phục vụ Job History (TEST 15).
    """
    jobs = await get_all_jobs_summary()
    return {
        "success": True,
        "total": len(jobs),
        "jobs": jobs,
    }


@router.delete("/jobs/{job_id}")
async def remove_job(job_id: str) -> Dict[str, Any]:
    """
    Xóa toàn bộ thư mục dữ liệu của Job.
    """
    ok = await delete_job(job_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy hoặc không thể xóa Job '{job_id}'.",
        )
    return {
        "success": True,
        "message": f"Đã xóa thành công Job '{job_id}'.",
        "job_id": job_id,
    }


@router.post("/jobs/{job_id}/retry")
async def retry_job(
    job_id: str,
    retry_req: RetryRequest,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    """
    Thực hiện Retry cho Job bị lỗi (Phase 1 / TEST 1 / TEST 10):
    - resume_from_failed=True: Giữ nguyên các stage đã completed trước đó, chỉ reset stage bị failed và các stage sau nó.
    - resume_from_failed=False: Reset toàn bộ pipeline về pending.
    """
    job_info = await load_job_info(job_id)
    if not job_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy Job '{job_id}'.",
        )

    # Double Retry Protection (Acceptance Test 33)
    if job_info.get("status") == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="JOB_ALREADY_PROCESSING: Tác vụ đang trong tiến trình xử lý, không thể chạy thử lại đồng thời.",
        )

    updated_job = await reset_failed_stages_for_retry(job_id, resume_from_failed=retry_req.resume_from_failed)
    if not updated_job:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể reset trạng thái Job để thử lại.",
        )

    cfg_dict = (
        retry_req.pipeline_config.dict()
        if retry_req.pipeline_config
        else job_info.get("config_snapshot", {})
    )
    req_obj = PipelineProcessRequest(**cfg_dict) if cfg_dict else PipelineProcessRequest()

    retry_plan = updated_job.get("retry_plan", {})
    resume_stage = retry_plan.get("resume_stage", "extract_audio") if retry_req.resume_from_failed else "extract_audio"

    # TEST 8: Error handling & Background task scheduling failure protection
    try:
        background_tasks.add_task(
            execute_pipeline_core,
            job_id,
            req_obj,
            resume_stage,
            retry_plan,
        )
    except Exception as e:
        await fail_stage(
            job_id,
            resume_stage,
            "RETRY_SCHEDULE_FAILED",
            f"Không thể lên lịch thử lại tác vụ: {str(e)}",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RETRY_SCHEDULE_FAILED: {str(e)}",
        )

    mode_str = "tiếp tục từ đoạn lỗi" if retry_req.resume_from_failed else "chạy lại từ đầu"
    stages = updated_job.get("stages", {})

    return {
        "success": True,
        "accepted": True,
        "mode": "resume" if retry_req.resume_from_failed else "full",
        "failed_stage": retry_plan.get("failed_stage"),
        "resume_stage": resume_stage,
        "retry_scope": retry_plan.get("retry_scope"),
        "preserve_upstream": retry_plan.get("preserve_upstream", False),
        "preserved_stages": retry_plan.get("preserved_stages", []),
        "execution_plan": retry_plan.get("execution_plan", CANONICAL_STAGE_ORDER),
        "message": f"Đang khởi chạy lại Job '{job_id}' ({mode_str}).",
        "job_id": job_id,
        "status": "processing",
        "current_stage": resume_stage,
        "retry_started": True,
        "retry_count": updated_job.get("retry_count", 1),
        "stages": stages,
        "progress": updated_job.get("progress", 0.0),
    }


@router.post("/batches/upload")
async def upload_batch_videos(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    """
    Tải lên từ 1 đến 5 video cùng lúc để tạo Batch (Phase 3 / TEST 5 / TEST 12):
    - Tối đa 5 video (MAX_BATCH_VIDEOS = 5).
    - Mỗi video được gán một Job ID độc lập, thư mục riêng biệt chống trùng lặp tên file.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng chọn ít nhất 1 file video.",
        )
    if len(files) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tối đa 5 video cho mỗi lượt xử lý batch (MAX_BATCH_VIDEOS=5).",
        )

    job_ids = []
    jobs_details = []
    for f in files:
        res = await _handle_single_video_upload(f)
        job_ids.append(res["job_id"])
        jobs_details.append(res)

    batch_info = await create_batch(job_ids)
    return {
        "success": True,
        "message": f"Đã tải lên thành công {len(job_ids)} video vào hàng đợi xử lý.",
        "batch_id": batch_info["batch_id"],
        "total_jobs": len(job_ids),
        "jobs": jobs_details,
        "batch": batch_info,
    }


@router.get("/batches/{batch_id}")
async def get_batch_status(batch_id: str) -> Dict[str, Any]:
    """
    Lấy thông tin và tiến độ của Batch (Phase 3 / TEST 11).
    """
    batch_info = await load_batch_info(batch_id)
    if not batch_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy Batch '{batch_id}'.",
        )

    enriched_jobs = []
    for j_id in batch_info.get("jobs", []):
        j_info = await load_job_info(j_id)
        if j_info:
            enriched_jobs.append(j_info)

    batch_info["jobs_detail"] = enriched_jobs
    batch_info["progress"] = await calculate_batch_progress(batch_info)
    return batch_info


@router.post("/batches/{batch_id}/process")
async def process_batch_queue(
    batch_id: str,
    request: PipelineProcessRequest,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    """
    Kích hoạt tiến trình xử lý tuần tự (Sequential Queue, Concurrency = 1) cho Batch:
    - Xử lý từng Job lần lượt.
    - Áp dụng Error Isolation: Job lỗi không dừng toàn bộ batch (TEST 4).
    """
    batch_info = await load_batch_info(batch_id)
    if not batch_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy Batch '{batch_id}'.",
        )

    async def _run_batch_worker():
        await update_batch_state(batch_id, status="processing")
        has_error = False
        for j_id in batch_info.get("jobs", []):
            await update_batch_state(batch_id, current_job_id=j_id)
            try:
                await execute_pipeline_core(j_id, request)
            except Exception as e:
                logger.error(f"Lỗi khi xử lý job {j_id} trong batch {batch_id}: {e}", exc_info=True)
                has_error = True

        final_status = "completed_with_errors" if has_error else "completed"
        await update_batch_state(batch_id, status=final_status)

    background_tasks.add_task(_run_batch_worker)

    return {
        "success": True,
        "message": f"Đã bắt đầu xử lý hàng đợi {batch_info.get('total_jobs', 0)} video.",
        "batch_id": batch_id,
        "status": "processing",
    }


@router.get("/jobs/{job_id}/subtitles")
@router.get("/jobs/{job_id}/translation")
async def get_job_subtitles(job_id: str) -> Dict[str, Any]:
    """
    Trả về danh sách các đoạn phụ đề / SpeechChunks đã nhận dạng hoặc đã dịch của Job.
    """
    job_paths = get_job_paths(job_id)
    if not job_paths:
        raise HTTPException(status_code=404, detail="Job not found")

    trans_file = job_paths["transcript_dir"] / "translated_transcript.json"
    stt_file = job_paths["transcript_dir"] / "transcript.json"

    if trans_file.exists():
        async with aiofiles.open(trans_file, "r", encoding="utf-8") as f:
            data = json.loads(await f.read())
            items = data.get("speech_chunks") or data.get("segments", [])
            return {
                "job_id": job_id,
                "has_translation": True,
                "target_language": data.get("target_language", "vi"),
                "items": items,
            }
    elif stt_file.exists():
        async with aiofiles.open(stt_file, "r", encoding="utf-8") as f:
            data = json.loads(await f.read())
            items = data.get("speech_chunks") or data.get("segments", [])
            return {
                "job_id": job_id,
                "has_translation": False,
                "source_language": data.get("detected_language", "en"),
                "items": items,
            }
    return {"job_id": job_id, "has_translation": False, "items": []}


@router.get("/jobs/{job_id}/video")
async def stream_job_video(job_id: str):
    """
    Phát video gốc đã tải lên của Job.
    """
    job_paths = get_job_paths(job_id)
    if not job_paths:
        raise HTTPException(status_code=404, detail="Job not found")

    video_files = list(job_paths["input_dir"].glob("*.*"))
    if not video_files:
        raise HTTPException(status_code=404, detail="Video file not found")

    video_path = video_files[0]
    return FileResponse(video_path, media_type="video/mp4", filename=video_path.name)


@router.get("/jobs/{job_id}/audio")
async def get_job_audio(job_id: str):
    """
    Phát file audio chất lượng cao đã trích xuất của Job.
    """
    job_paths = get_job_paths(job_id)
    if not job_paths:
        raise HTTPException(status_code=404, detail="Job not found")

    audio_path = job_paths["audio_dir"] / "original_audio.wav"
    if not audio_path.exists():
        audio_path = job_paths["audio_dir"] / "original.wav"
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(audio_path, media_type="audio/wav", filename=audio_path.name)


@router.post("/jobs/{job_id}/stt")
async def process_speech_to_text(job_id: str, request: STTRequest) -> Dict[str, Any]:
    """
    Nhận diện giọng nói từ file audio WAV (whisper.wav) của Job bằng Faster-Whisper (có Word Timestamps).
    """
    job_paths = get_job_paths(job_id)
    if not job_paths:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy Job có ID '{job_id}'.",
        )

    # Ưu tiên lấy file whisper.wav 16kHz chuẩn
    whisper_audio_path = job_paths["audio_dir"] / "whisper.wav"
    if not whisper_audio_path.exists():
        whisper_audio_path = job_paths["audio_dir"] / "original.wav"
    if not whisper_audio_path.exists():
        whisper_audio_path = job_paths["audio_dir"] / "original_audio.wav"
    if not whisper_audio_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File audio WAV chưa được trích xuất cho Job này.",
        )

    if request.model not in VALID_WHISPER_MODELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"INVALID_WHISPER_MODEL: Model Whisper '{request.model}' không hợp lệ. Các model hỗ trợ: {', '.join(sorted(VALID_WHISPER_MODELS))}",
        )

    output_transcript_path = job_paths["transcript_dir"] / "transcript.json"

    try:
        stt_result = await transcribe_audio(
            audio_path=whisper_audio_path,
            output_transcript_path=output_transcript_path,
            model_size=request.model,
            language=request.language,
        )
        # Tạo Semantic SpeechChunks ngay sau khi STT xong
        raw_segments = stt_result.get("segments", [])
        speech_chunks = build_speech_chunks_from_stt(raw_segments)
        stt_result["speech_chunks"] = speech_chunks
        stt_result["total_speech_chunks"] = len(speech_chunks)

        async with aiofiles.open(output_transcript_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(stt_result, indent=2, ensure_ascii=False))

    except Exception as e:
        logger.error(f"Lỗi nhận diện STT cho job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi trong quá trình nhận diện giọng nói: {str(e)}",
        )

    # Cập nhật thông tin vào job_info.json
    job_info_file = job_paths["job_dir"] / "job_info.json"
    job_info = {}
    if job_info_file.exists():
        try:
            async with aiofiles.open(job_info_file, "r", encoding="utf-8") as jf:
                job_info = json.loads(await jf.read())
        except Exception:
            pass

    job_info["status"] = "stt_completed"
    job_info["stage"] = "mvp_2_completed"
    job_info["stt_config"] = {
        "model": request.model,
        "language": request.language,
        "detected_language": stt_result.get("detected_language"),
        "language_probability": stt_result.get("language_probability"),
        "total_segments": stt_result.get("total_segments"),
        "total_speech_chunks": len(speech_chunks),
    }

    async with aiofiles.open(job_info_file, "w", encoding="utf-8") as jf:
        await jf.write(json.dumps(job_info, indent=2, ensure_ascii=False))

    return {
        "success": True,
        "message": f"Nhận diện giọng nói thành công ({stt_result.get('total_segments')} segments, {len(speech_chunks)} SpeechChunks).",
        "job_id": job_id,
        "detected_language": stt_result.get("detected_language"),
        "language_probability": stt_result.get("language_probability"),
        "duration": stt_result.get("duration"),
        "total_segments": stt_result.get("total_segments"),
        "total_speech_chunks": len(speech_chunks),
        "segments": speech_chunks if speech_chunks else stt_result.get("segments"),
        "speech_chunks": speech_chunks,
    }


@router.get("/jobs/{job_id}/transcript")
async def get_job_transcript(job_id: str) -> Dict[str, Any]:
    """
    Lấy nội dung file transcript JSON của Job.
    """
    job_paths = get_job_paths(job_id)
    if not job_paths:
        raise HTTPException(status_code=404, detail="Job not found")

    trans_trans_file = job_paths["transcript_dir"] / "translated_transcript.json"
    orig_trans_file = job_paths["transcript_dir"] / "transcript.json"

    target_file = trans_trans_file if trans_trans_file.exists() else orig_trans_file
    if not target_file.exists():
        raise HTTPException(status_code=404, detail="Transcript not found")

    async with aiofiles.open(target_file, "r", encoding="utf-8") as f:
        data = json.loads(await f.read())

    return data


@router.post("/jobs/{job_id}/translate")
async def translate_job_transcript(job_id: str, request: TranslateRequest) -> Dict[str, Any]:
    """
    Dịch toàn bộ SpeechChunks của Job sang ngôn ngữ đích bằng Gemini API (Spoken Narration & Duration-aware).
    """
    job_paths = get_job_paths(job_id)
    if not job_paths:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy Job có ID '{job_id}'.",
        )

    transcript_path = job_paths["transcript_dir"] / "transcript.json"
    if not transcript_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chưa có dữ liệu nhận diện giọng nói (STT). Vui lòng thực hiện STT trước khi dịch.",
        )

    async with aiofiles.open(transcript_path, "r", encoding="utf-8") as tf:
        transcript_data = json.loads(await tf.read())

    # Sử dụng hoặc tái tạo SpeechChunks
    speech_chunks = transcript_data.get("speech_chunks")
    if not speech_chunks:
        raw_segments = transcript_data.get("segments", [])
        speech_chunks = build_speech_chunks_from_stt(raw_segments)

    # Chuẩn bị file chứa chunks cho translation service
    chunks_temp_file = job_paths["transcript_dir"] / "chunks_for_translation.json"
    chunks_payload = {
        "detected_language": transcript_data.get("detected_language", "en"),
        "duration": transcript_data.get("duration", 0),
        "segments": speech_chunks,
    }
    async with aiofiles.open(chunks_temp_file, "w", encoding="utf-8") as cf:
        await cf.write(json.dumps(chunks_payload, indent=2, ensure_ascii=False))

    translated_transcript_path = job_paths["transcript_dir"] / "translated_transcript.json"

    try:
        translation_style = request.translation_style or "standard_dubbing"
        translation_result = await translate_transcript_segments(
            transcript_file=chunks_temp_file,
            output_translated_file=translated_transcript_path,
            target_language=request.target_language,
            source_language=request.source_language,
            api_key=request.api_key,
            translation_style=translation_style,
        )
        # Lưu kèm cấu trúc gốc để đồng bộ
        translation_result["speech_chunks"] = translation_result.get("segments", speech_chunks)
        translation_result["original_raw_segments"] = transcript_data.get("segments", [])
        async with aiofiles.open(translated_transcript_path, "w", encoding="utf-8") as out_f:
            await out_f.write(json.dumps(translation_result, indent=2, ensure_ascii=False))

    except Exception as e:
        logger.error(f"Lỗi dịch thuật cho job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi dịch thuật Gemini: {str(e)}",
        )

    # Cập nhật thông tin vào job_info.json
    job_info_file = job_paths["job_dir"] / "job_info.json"
    job_info = {}
    if job_info_file.exists():
        try:
            async with aiofiles.open(job_info_file, "r", encoding="utf-8") as jf:
                job_info = json.loads(await jf.read())
        except Exception:
            pass

    job_info["status"] = "translation_completed"
    job_info["stage"] = "mvp_3_completed"
    job_info["translation_config"] = {
        "target_language": request.target_language,
        "source_language": request.source_language,
        "translation_style": translation_style,
        "translated_segments": translation_result.get("translated_segments"),
        "model_used": translation_result.get("model_used"),
    }

    async with aiofiles.open(job_info_file, "w", encoding="utf-8") as jf:
        await jf.write(json.dumps(job_info, indent=2, ensure_ascii=False))

    return {
        "success": True,
        "message": f"Dịch thuật thuyết minh ({translation_style}) thành công {translation_result.get('translated_segments')} câu thoại.",
        "job_id": job_id,
        "target_language": request.target_language,
        "translation_style": translation_style,
        "model_used": translation_result.get("model_used"),
        "total_segments": translation_result.get("total_segments"),
        "translated_segments": translation_result.get("translated_segments"),
        "segments": translation_result.get("segments"),
        "speech_chunks": translation_result.get("segments"),
    }


@router.get("/tts/voices")
async def list_available_voices(language: str = Query(default="vi")) -> Dict[str, Any]:
    """
    Lấy danh sách các giọng đọc AI phong phú (Edge-TTS) theo ngôn ngữ.
    """
    voices = get_available_voices(language)
    return {
        "language": language,
        "voices": voices,
        "count": len(voices),
    }


@router.post("/tts/preview")
async def preview_voice_audio(request: VoicePreviewRequest):
    """
    Sinh audio nghe thử giọng đọc AI nhanh theo văn bản mẫu (KHÔNG áp dụng atempo sync).
    """
    temp_preview_dir = Path("data/temp_preview")
    temp_preview_dir.mkdir(parents=True, exist_ok=True)
    preview_file = temp_preview_dir / f"preview_{abs(hash(request.text + request.voice + request.speed_rate))}.mp3"

    resolved = resolve_effective_tts_speed(request.voice, request.speed_rate)
    logger.info(
        f"TTS_PREVIEW: voice_id='{request.voice}', base_voice='{resolved['base_voice']}', "
        f"preview_rate='{resolved['rate']}', preview_pitch='{resolved['pitch']}', "
        f"pause_profile='{resolved['pause_profile']}', rec_style='{resolved['recommended_translation_style']}'"
    )

    try:
        await generate_speech_for_text(
            text=request.text,
            output_path=preview_file,
            voice=request.voice,
            speed_rate=request.speed_rate,
        )
    except Exception as e:
        logger.error(f"Lỗi tạo preview audio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi tạo preview giọng đọc: {str(e)}",
        )

    return FileResponse(preview_file, media_type="audio/mpeg", filename="preview.mp3")


@router.post("/jobs/{job_id}/dub-and-render")
async def dub_and_render_video(
    job_id: str,
    request: DubAndRenderRequest,
) -> Dict[str, Any]:
    """
    Toàn bộ quy trình MVP 4 & MVP 5:
    1. Lấy SpeechSegments từ transcript dịch thuật
    2. Sinh giọng đọc AI (TTS) từng câu
    3. Phân đoạn SubtitleSegments & xuất file .SRT (Subtitle Validator)
    4. Đồng bộ thời lượng & chèn Breathing Pause động (48kHz Stereo) theo pause_profile của preset
    5. Mix Original Background Audio (48kHz) + AI Voice (48kHz) + Loudness Normalization
    6. Xuất video MP4 H.264/AAC 48kHz và tự động chạy post-render validation
    """
    job_paths = get_job_paths(job_id)
    if not job_paths:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy Job có ID '{job_id}'.",
        )

    # 1. Tìm transcript đã dịch
    trans_file = job_paths["transcript_dir"] / "translated_transcript.json"
    if not trans_file.exists():
        trans_file = job_paths["transcript_dir"] / "transcript.json"
    async with aiofiles.open(trans_file, "r", encoding="utf-8") as tf:
        transcript_data = json.loads(await tf.read())

    speech_chunks = transcript_data.get("speech_chunks")
    if not speech_chunks:
        raw_segments = transcript_data.get("segments", [])
        speech_chunks = build_speech_chunks_from_stt(raw_segments)
        # Nếu segments đã được dịch mà chunks chưa có dịch, gán translated_text
        if not any(c.get("translated_text") for c in speech_chunks):
            for c in speech_chunks:
                c["translated_text"] = c.get("original_text", "")

    if not speech_chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transcript không chứa câu thoại nào để lồng tiếng.",
        )

    # 2. Tìm video gốc và audio gốc 48kHz
    video_files = list(job_paths["input_dir"].glob("*.*"))
    if not video_files:
        raise HTTPException(status_code=404, detail="Không tìm thấy file video gốc.")
    input_video_path = video_files[0]

    original_audio_path = job_paths["audio_dir"] / "original_audio.wav"
    if not original_audio_path.exists():
        original_audio_path = job_paths["audio_dir"] / "original.wav"

    video_info = await get_video_info(input_video_path)
    total_video_duration = float(video_info.get("duration", 0.0))

    # 3. Phân giải cấu hình Preset và Pause Profile từ metadata
    voice_meta = get_voice_preset_metadata(request.voice)
    resolved_speed = resolve_effective_tts_speed(request.voice, request.speed_rate)
    pause_profile = voice_meta.get("pause_profile", "standard")

    async def update_progress(percent: int, message: str, stage: str = "dubbing"):
        try:
            j_file = job_paths["job_dir"] / "job_info.json"
            j_data = {}
            if j_file.exists():
                async with aiofiles.open(j_file, "r", encoding="utf-8") as f:
                    j_data = json.loads(await f.read())
            j_data["progress"] = {
                "percent": percent,
                "message": message,
                "stage": stage,
            }
            async with aiofiles.open(j_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(j_data, indent=2, ensure_ascii=False))
        except Exception:
            pass

    try:
        # Bước A: Sinh audio TTS theo từng SpeechChunk (Câu/Ý hoàn chỉnh liền mạch)
        total_chunks_count = len(speech_chunks)
        await update_progress(10, f"Bắt đầu sinh giọng đọc AI cho {total_chunks_count} câu thoại...", "tts")
        logger.info(
            f"Bắt đầu sinh TTS cho {total_chunks_count} SpeechChunks (voice={request.voice}, "
            f"synthesis_rate={resolved_speed['rate']}, pitch={resolved_speed['pitch']})..."
        )
        
        async def on_tts_progress(completed: int, total: int):
            pct = int(10 + (completed / max(1, total)) * 50)  # 10% -> 60%
            await update_progress(pct, f"Đang sinh giọng đọc AI ({completed}/{total} câu thoại)...", "tts")

        tts_segments = await generate_all_segments(
            segments=speech_chunks,
            voice=request.voice,
            tts_dir=job_paths["tts_dir"],
            speed_rate=request.speed_rate,
            progress_callback=on_tts_progress,
        )

        # Bước B: Phân đoạn SubtitleSegments độc lập & xuất file .SRT (kèm Short Fragment Merger & CPS Balancer)
        await update_progress(65, "Đang phân đoạn và xuất file phụ đề chuẩn .SRT...", "subtitles")
        srt_file = job_paths["subtitles_dir"] / "translated.srt"
        _, valid_subs, subtitle_summary = await save_srt_file(
            speech_segments=speech_chunks,
            output_srt_path=srt_file,
        )

        # Bước C: Đồng bộ thời lượng & chèn Deterministic Natural Pause (48kHz Stereo) theo pause_profile
        await update_progress(75, f"Đang đồng bộ nhịp điệu ({pause_profile}) và ghép track 48kHz Stereo...", "sync")
        dubbed_voice_wav = job_paths["audio_dir"] / "dubbed_voice.wav"
        temp_sync_dir = job_paths["audio_dir"] / "sync_temp"
        _, sync_stats = await sync_and_combine_voice_track(
            tts_segments=tts_segments,
            output_dubbed_wav=dubbed_voice_wav,
            total_video_duration=total_video_duration,
            temp_sync_dir=temp_sync_dir,
            pause_profile=pause_profile,
        )
        sync_stats["synthesis_rate_percent"] = resolved_speed["synthesis_rate_percent"]

        # Bước D: Mix background audio (48kHz) + voice (48kHz) + loudnorm và render video hoàn chỉnh
        await update_progress(85, "Đang mix âm thanh nền + giọng AI và render video MP4 hoàn chỉnh...", "render")
        output_final_mp4 = job_paths["output_dir"] / "final_dubbed.mp4"
        render_result = await render_final_video(
            input_video_path=input_video_path,
            original_audio_path=original_audio_path,
            dubbed_audio_path=dubbed_voice_wav,
            output_video_path=output_final_mp4,
            srt_subtitle_path=srt_file,
            keep_background_audio=request.keep_background_audio,
            background_volume=request.background_volume,
            voice_volume=request.voice_volume,
            burn_subtitles=request.burn_subtitles,
        )

        # Bước E: Độc lập đo kiểm toàn diện Pipeline Metrics
        orig_whisper_count = len(transcript_data.get("original_raw_segments") or transcript_data.get("segments", speech_chunks))
        pipeline_metrics = compute_pipeline_metrics(
            speech_chunks=speech_chunks,
            subtitles=valid_subs,
            sync_stats=sync_stats,
            original_whisper_count=orig_whisper_count,
            expected_total_duration=total_video_duration,
            synthesis_rate_percent=resolved_speed["synthesis_rate_percent"],
        )
        await update_progress(100, "Hoàn tất lồng tiếng và render video thành công!", "completed")

    except Exception as e:
        logger.error(f"Lỗi khi thực thi Dub & Render: {e}", exc_info=True)
        await update_progress(0, f"Lỗi: {str(e)}", "error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi xử lý lồng tiếng và xuất video: {str(e)}",
        )



    # Cập nhật job_info.json
    job_info_file = job_paths["job_dir"] / "job_info.json"
    job_info = {}
    if job_info_file.exists():
        try:
            async with aiofiles.open(job_info_file, "r", encoding="utf-8") as jf:
                job_info = json.loads(await jf.read())
        except Exception:
            pass

    job_info["status"] = "completed"
    job_info["stage"] = "mvp_5_completed"
    job_info["dub_config"] = {
        "voice": request.voice,
        "speed_rate": request.speed_rate,
        "pause_profile": pause_profile,
        "synthesis_rate_percent": resolved_speed["synthesis_rate_percent"],
        "resolved_rate": resolved_speed["rate"],
        "resolved_pitch": resolved_speed["pitch"],
        "keep_background_audio": request.keep_background_audio,
        "background_volume": request.background_volume,
        "voice_volume": request.voice_volume,
        "burn_subtitles": request.burn_subtitles,
    }
    job_info["subtitles_summary"] = subtitle_summary
    job_info["pipeline_metrics"] = pipeline_metrics
    job_info["render_validation"] = render_result.get("validation")
    job_info["output"] = {
        "video_path": str(output_final_mp4),
        "duration": render_result.get("duration"),
        "duration_formatted": render_result.get("duration_formatted"),
        "size": format_file_size(render_result.get("size_bytes", 0)),
        "resolution": render_result.get("resolution"),
    }

    async with aiofiles.open(job_info_file, "w", encoding="utf-8") as jf:
        await jf.write(json.dumps(job_info, indent=2, ensure_ascii=False))

    return {
        "success": True,
        "message": "Lồng tiếng AI và render video 48kHz Stereo hoàn tất thành công.",
        "job_id": job_id,
        "video": {
            "filename": output_final_mp4.name,
            "duration": render_result.get("duration"),
            "duration_formatted": render_result.get("duration_formatted"),
            "size": format_file_size(render_result.get("size_bytes", 0)),
            "resolution": render_result.get("resolution"),
            "video_url": f"/api/jobs/{job_id}/result/video",
            "download_video_url": f"/api/jobs/{job_id}/download/video",
            "download_srt_url": f"/api/jobs/{job_id}/download/subtitle",
        },
        "pipeline_metrics": pipeline_metrics,
        "subtitle_validation": subtitle_summary,
        "render_validation": render_result.get("validation"),
    }


@router.get("/jobs/{job_id}/result/video")
async def stream_result_video(job_id: str, v: Optional[str] = Query(None)):
    """
    Stream video thành phẩm cho thẻ <video> trên giao diện web (có Cache-Busting qua query v={output_revision}).
    """
    job_paths = get_job_paths(job_id)
    if not job_paths:
        raise HTTPException(status_code=404, detail="Job not found")

    final_video = job_paths["output_dir"] / "final_dubbed.mp4"
    if not final_video.exists():
        raise HTTPException(status_code=404, detail="File video hoàn chỉnh chưa được tạo.")

    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    return FileResponse(final_video, media_type="video/mp4", filename="final_dubbed.mp4", headers=headers)


@router.get("/jobs/{job_id}/download/video")
async def download_result_video(job_id: str, v: Optional[str] = Query(None)):
    """
    Tải file video MP4 hoàn chỉnh về máy người dùng.
    """
    job_paths = get_job_paths(job_id)
    if not job_paths:
        raise HTTPException(status_code=404, detail="Job not found")

    final_video = job_paths["output_dir"] / "final_dubbed.mp4"
    if not final_video.exists():
        raise HTTPException(status_code=404, detail="File video chưa được tạo.")

    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    return FileResponse(
        final_video,
        media_type="application/octet-stream",
        filename="final_dubbed.mp4",
        headers=headers,
    )


@router.get("/jobs/{job_id}/download/subtitle")
async def download_result_subtitle(
    job_id: str,
    type: str = Query("translated"),
    v: Optional[str] = Query(None),
):
    """
    Tải file phụ đề chuẩn .SRT về máy người dùng (hỗ trợ cả phụ đề dịch và phụ đề gốc).
    Tự động bảo đảm canonical SRT artifact tồn tại từ segments mà KHÔNG gọi lại Gemini.
    """
    job_paths = get_job_paths(job_id)
    if not job_paths:
        raise HTTPException(status_code=404, detail="Job not found")

    sub_type = "original" if str(type).lower() in ["original", "goc", "source"] else "translated"
    filename = "original.srt" if sub_type == "original" else "translated.srt"

    try:
        srt_file = await ensure_subtitle_artifact(job_id, job_paths, subtitle_type=sub_type)
    except Exception as e:
        logger.error(f"Lỗi khi bảo đảm SRT ({sub_type}) cho job {job_id}: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"File phụ đề {filename} chưa được tạo hoặc không tìm thấy dữ liệu bản dịch.",
        )

    if not srt_file.exists() or srt_file.stat().st_size == 0:
        raise HTTPException(status_code=404, detail=f"File phụ đề {filename} rỗng hoặc không tồn tại.")

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "no-cache, no-store, must-revalidate",
    }
    return FileResponse(
        srt_file,
        media_type="application/x-subrip",
        filename=filename,
        headers=headers,
    )


@router.post("/jobs/{job_id}/process")
async def process_job_pipeline(
    job_id: str,
    request: PipelineProcessRequest,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    """
    Điểm điều phối Pipeline duy nhất (Unified Pipeline Orchestrator).
    Nhận snapshot cấu hình, giải quyết dependencies, tái sử dụng artifacts hợp lệ,
    chống double-start (HTTP 409), khởi chạy worker nền và trả về phản hồi tức thì.
    """
    job_paths = get_job_paths(job_id)
    if not job_paths:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy Job có ID '{job_id}'.",
        )

    # 1. Validate Whisper Model
    if request.whisper_model not in VALID_WHISPER_MODELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"INVALID_WHISPER_MODEL: Model Whisper '{request.whisper_model}' không hợp lệ. Các model hỗ trợ: {', '.join(sorted(VALID_WHISPER_MODELS))}",
        )

    job_info = await load_job_info(job_id) or create_initial_job_state(job_id)

    # 2. Double-Start Protection
    if job_info.get("status") == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job đang được xử lý trong một tiến trình khác. Vui lòng chờ hoàn tất.",
        )

    stages = job_info.setdefault("stages", {})
    has_completed_stages = any(s.get("status") == "completed" for s in stages.values())
    old_config = job_info.get("config_snapshot")
    new_config = request.dict()

    resume_stage = "extract_audio"
    retry_plan = None

    if has_completed_stages:
        # Reprocess / Rerun with dependency resolution
        dirty_stages = compute_dirty_stages(old_config, new_config, stages)
        if not dirty_stages:
            dirty_stages = ["render"]

        updated_job = await prepare_job_for_reprocess(job_id, new_config, dirty_stages)
        if updated_job:
            job_info = updated_job
            retry_plan = updated_job.get("retry_plan", {})
            resume_stage = retry_plan.get("resume_stage", dirty_stages[0])
    else:
        # Initial run
        is_sub_enabled = getattr(request, "subtitle_enabled", True) and request.create_subtitle
        needs_audio = request.run_stt or request.run_translation or request.run_tts or request.render_video
        needs_stt = request.run_stt or (request.run_translation or request.run_tts or request.render_video or is_sub_enabled)
        needs_translation = request.run_translation or request.run_tts or (request.render_video and is_sub_enabled)
        needs_tts = request.run_tts or request.render_video
        needs_subtitle = is_sub_enabled
        needs_render = request.render_video

        job_info["status"] = "processing"
        job_info["config_snapshot"] = new_config

        stage_flags = [
            ("extract_audio", needs_audio),
            ("stt", needs_stt),
            ("translation", needs_translation),
            ("tts", needs_tts),
            ("audio_sync", needs_tts),
            ("subtitle", needs_subtitle),
            ("render", needs_render),
        ]

        for s_name, is_enabled in stage_flags:
            if s_name in stages:
                if is_enabled:
                    if stages[s_name].get("status") != "completed":
                        stages[s_name]["status"] = "pending"
                        stages[s_name]["message"] = "Chờ xử lý"
                else:
                    stages[s_name]["status"] = "skipped"
                    stages[s_name]["message"] = "Bỏ qua theo tùy chọn"

        await save_job_info_atomic(job_id, job_info)

    # Đưa tác vụ chạy nền
    background_tasks.add_task(execute_pipeline_core, job_id, request, resume_stage, retry_plan)

    return {
        "success": True,
        "message": "Đã bắt đầu tiến trình xử lý pipeline.",
        "job_id": job_id,
        "status": "processing",
        "resume_stage": resume_stage,
        "stages": job_info.get("stages", {}),
    }


async def execute_pipeline_core(
    job_id: str,
    request: PipelineProcessRequest,
    resume_stage: Optional[str] = None,
    retry_plan: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Worker thực thi toàn bộ pipeline ngầm trong Background Task với chính sách Strict RetryPlan & Hard Invariant Guard:
    - RetryPlan Precedence: Nếu resume_stage="tts", các stage trước đó (extract_audio, stt, translation) bị cấm chạy lại hoàn toàn.
    - Hard Invariant Guard: assert_stage_allowed ngăn chặn mọi attempt gọi service upstream khi stage_index < resume_index.
    - CANONICAL_STAGE_ORDER slicing: Chỉ thực thi các stage trong execution_plan.
    """
    job_paths = get_job_paths(job_id)
    if not job_paths:
        return {}

    job_info = await load_job_info(job_id) or create_initial_job_state(job_id)
    job_info["config_snapshot"] = request.dict()

    # 1. Xác định Execution Plan và Hard Invariant Guard
    effective_retry_plan = retry_plan or job_info.get("retry_plan") or {}
    if effective_retry_plan.get("execution_plan"):
        execution_plan = effective_retry_plan["execution_plan"]
        preserved_stages = effective_retry_plan.get("preserved_stages", [s for s in CANONICAL_STAGE_ORDER if s not in execution_plan])
        resume_stage_clean = effective_retry_plan.get("resume_stage") or execution_plan[0]
        resume_idx = effective_retry_plan.get("resume_index", CANONICAL_STAGE_ORDER.index(resume_stage_clean) if resume_stage_clean in CANONICAL_STAGE_ORDER else 0)
    else:
        resume_stage_clean = resume_stage or effective_retry_plan.get("resume_stage") or "extract_audio"
        resume_idx = CANONICAL_STAGE_ORDER.index(resume_stage_clean) if resume_stage_clean in CANONICAL_STAGE_ORDER else 0
        preserved_stages = CANONICAL_STAGE_ORDER[:resume_idx]
        execution_plan = CANONICAL_STAGE_ORDER[resume_idx:]

    logger.info(
        f"[PIPELINE] job_id={job_id} mode={'resume' if resume_idx > 0 else 'full'} "
        f"failed_stage={retry_plan.get('failed_stage') if retry_plan else None} resume_stage={resume_stage_clean} "
        f"preserved={preserved_stages} execution_plan={execution_plan}"
    )

    def assert_stage_allowed(stage_name: str):
        if stage_name in preserved_stages or stage_name not in execution_plan:
            err_msg = (
                f"HARD_GUARD_VIOLATION: Stage '{stage_name}' is in preserved_stages or not in execution_plan "
                f"and is strictly FORBIDDEN from running when execution plan is {execution_plan}!"
            )
            logger.error(err_msg)
            raise RuntimeError(err_msg)

    # Helper tạo callback cập nhật realtime khi stage-level retry diễn ra
    def _make_retry_callbacks(stage_name: str, stage_label: str):
        async def _on_retry(attempt: int, max_att: int, exc: Exception, wait_sec: float):
            msg = f"Lỗi tạm thời ({str(exc)[:40]}). Đang tự thử lại {stage_label} (lần {attempt}/{max_att - 1})..."
            await update_stage_retry(job_id, stage_name, attempt=attempt, max_attempts=max_att, message=msg)

        async def _on_recovered(attempt: int):
            msg = f"✓ Đã khôi phục. Đang tiếp tục {stage_label}..."
            await update_stage_progress(job_id, stage_name, message=msg)

        return _on_retry, _on_recovered

    # Xác định các stage enabled vs skipped
    is_sub_enabled = getattr(request, "subtitle_enabled", True) and request.create_subtitle
    sub_mode = getattr(request, "subtitle_mode", "burn" if request.burn_subtitles else "none")

    needs_audio = request.run_stt or request.run_translation or request.run_tts or request.render_video
    needs_stt = request.run_stt or (request.run_translation or request.run_tts or request.render_video or is_sub_enabled)
    needs_translation = request.run_translation or request.run_tts or (request.render_video and is_sub_enabled)
    needs_tts = request.run_tts or request.render_video
    needs_subtitle = is_sub_enabled
    needs_render = request.render_video
    should_burn_subs = is_sub_enabled and (sub_mode == "burn" or request.burn_subtitles)

    current_running_stage = resume_stage_clean
    current_task = asyncio.current_task()
    if current_task:
        register_active_task(job_id, current_task)

    job_info["worker_instance_id"] = RUNTIME_INSTANCE_ID
    await save_job_info_atomic(job_id, job_info)

    try:
        # Tìm file video đầu vào
        input_video_files = list(job_paths["input_dir"].glob("*"))
        if not input_video_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="INPUT_FILE_MISSING: Không tìm thấy file video gốc của Job này.",
            )
        input_video_path = input_video_files[0]

        # Đường dẫn các artifacts trung gian
        whisper_audio_path = job_paths["audio_dir"] / "whisper.wav"
        original_audio_path = job_paths["audio_dir"] / "original_audio.wav"
        transcript_path = job_paths["transcript_dir"] / "transcript.json"
        translated_path = job_paths["transcript_dir"] / "translated_transcript.json"
        srt_file = job_paths["subtitles_dir"] / "translated.srt"
        ass_file = job_paths["subtitles_dir"] / "translated.ass"
        dubbed_voice_wav = job_paths["output_dir"] / "dubbed_voice.wav"
        output_final_mp4 = job_paths["output_dir"] / f"final_dubbed.{request.output_format}"

        raw_segments: List[Dict[str, Any]] = []
        speech_chunks: List[Dict[str, Any]] = []
        translated_chunks: List[Dict[str, Any]] = []
        detected_lang = "en"
        valid_subs: List[Dict[str, Any]] = []
        subtitle_summary: Dict[str, Any] = {}
        tts_segments: List[Dict[str, Any]] = []
        sync_stats: Dict[str, Any] = {}
        render_result: Dict[str, Any] = {}
        pipeline_metrics: Dict[str, Any] = {}

        # -------------------------------------------------------------
        # STEP 1: Dual Audio Extraction
        # -------------------------------------------------------------
        if "extract_audio" in execution_plan:
            assert_stage_allowed("extract_audio")
            current_running_stage = "extract_audio"
            if needs_audio:
                if not whisper_audio_path.exists() or not original_audio_path.exists():
                    await start_stage(job_id, "extract_audio", "Đang trích xuất Dual Audio 48kHz Stereo & 16kHz Mono...")
                    on_retry_cb, on_rec_cb = _make_retry_callbacks("extract_audio", "trích xuất âm thanh")
                    logger.info("[PIPELINE_EXEC] stage=extract_audio service=extract_dual_audio")
                    audio_info = await execute_with_auto_retry(
                        extract_dual_audio,
                        video_path=input_video_path,
                        audio_dir=job_paths["audio_dir"],
                        stage_name="extract_audio",
                        on_retry_callback=on_retry_cb,
                        on_recovered_callback=on_rec_cb,
                    )
                    job_info["audio_info"] = audio_info
                    await complete_stage(job_id, "extract_audio", "Trích xuất Dual Audio hoàn tất (48kHz Stereo + 16kHz Mono)")
                else:
                    await start_stage(job_id, "extract_audio", "Đang nạp file âm thanh 48kHz & 16kHz đã có...")
                    await complete_stage(job_id, "extract_audio", "Tái sử dụng file âm thanh 48kHz & 16kHz đã có")
            else:
                await skip_stage(job_id, "extract_audio", "Bỏ qua trích xuất âm thanh")
        else:
            logger.info("[PIPELINE] stage=extract_audio preserved from previous run (ZERO INVOCATION)")

        # -------------------------------------------------------------
        # STEP 2: Whisper STT
        # -------------------------------------------------------------
        if "stt" in execution_plan:
            assert_stage_allowed("stt")
            current_running_stage = "stt"
            if needs_stt:
                can_reuse_stt = transcript_path.exists() and not request.run_stt
                if not can_reuse_stt:
                    await start_stage(job_id, "stt", f"Đang nhận dạng giọng nói với Faster-Whisper ({request.whisper_model})...")

                    async def _on_stt_progress(pct: float, msg: str):
                        await update_stage_progress(job_id, "stt", progress=pct, message=msg)

                    on_retry_cb, on_rec_cb = _make_retry_callbacks("stt", "nhận dạng giọng nói")
                    logger.info("[PIPELINE_EXEC] stage=stt service=transcribe_audio")
                    stt_result = await execute_with_auto_retry(
                        transcribe_audio,
                        audio_path=whisper_audio_path,
                        output_transcript_path=transcript_path,
                        model_size=request.whisper_model,
                        language=None if request.source_language == "auto" else request.source_language,
                        progress_callback=_on_stt_progress,
                        stage_name="stt",
                        on_retry_callback=on_retry_cb,
                        on_recovered_callback=on_rec_cb,
                    )
                    raw_segments = stt_result.get("segments", [])
                    speech_chunks = stt_result.get("speech_chunks", [])
                    detected_lang = stt_result.get("detected_language", "en")

                    job_info["transcript"] = {
                        "total_segments": len(raw_segments),
                        "total_speech_chunks": len(speech_chunks),
                        "language": detected_lang,
                    }
                    await complete_stage(job_id, "stt", f"Hoàn thành nhận dạng: {len(raw_segments)} đoạn thoại ({len(speech_chunks)} SpeechChunks)")
                else:
                    await start_stage(job_id, "stt", "Đang nạp transcript.json đã lưu...")
                    async with aiofiles.open(transcript_path, "r", encoding="utf-8") as f:
                        cached_stt = json.loads(await f.read())
                        raw_segments = cached_stt.get("segments", [])
                        speech_chunks = cached_stt.get("speech_chunks", [])
                        if not speech_chunks and raw_segments:
                            speech_chunks = build_speech_chunks_from_stt(raw_segments)
                        detected_lang = cached_stt.get("detected_language", "en")
                    await complete_stage(job_id, "stt", f"Tái sử dụng transcript {len(speech_chunks)} SpeechChunks đã có")
            else:
                await skip_stage(job_id, "stt", "Bỏ qua nhận dạng giọng nói")
        else:
            logger.info("[PIPELINE] stage=stt preserved from previous run (ZERO INVOCATION)")
            if transcript_path.exists():
                async with aiofiles.open(transcript_path, "r", encoding="utf-8") as f:
                    cached_stt = json.loads(await f.read())
                    raw_segments = cached_stt.get("segments", [])
                    speech_chunks = cached_stt.get("speech_chunks", [])
                    if not speech_chunks and raw_segments:
                        speech_chunks = build_speech_chunks_from_stt(raw_segments)
                    detected_lang = cached_stt.get("detected_language", "en")

        # -------------------------------------------------------------
        # STEP 3: Gemini Translation
        # -------------------------------------------------------------
        if "translation" in execution_plan:
            assert_stage_allowed("translation")
            current_running_stage = "translation"
            if needs_translation:
                cached_trans = None
                if translated_path.exists():
                    try:
                        async with aiofiles.open(translated_path, "r", encoding="utf-8") as f:
                            cached_trans = json.loads(await f.read())
                    except Exception:
                        cached_trans = None

                can_reuse_translation = (
                    cached_trans is not None
                    and not request.run_translation
                    and cached_trans.get("target_language") == request.target_language
                    and (
                        not request.translation_style
                        or cached_trans.get("translation_style") == request.translation_style
                        or not cached_trans.get("translation_style")
                    )
                )

                if not can_reuse_translation:
                    await start_stage(job_id, "translation", f"Đang dịch thuật ngữ cảnh ({request.translation_style or 'standard_dubbing'})...")

                    async def _on_trans_progress(completed_count: int, total_count: int, message: Optional[str] = None):
                        pct = round((completed_count / max(1, total_count)) * 100.0, 1)
                        msg = message or f"Đang dịch {completed_count}/{total_count} câu ({pct}%)"
                        await update_stage_progress(
                            job_id,
                            "translation",
                            progress=pct,
                            message=msg,
                            extra={"translated_chunks": completed_count, "total_chunks": total_count},
                        )

                    logger.info("[PIPELINE_EXEC] stage=translation service=translate_transcript_segments")
                    trans_result = await translate_transcript_segments(
                        transcript_file=transcript_path,
                        output_translated_file=translated_path,
                        source_language=detected_lang,
                        target_language=request.target_language,
                        api_key=request.api_key,
                        translation_style=request.translation_style or "movie_review_spoken_vi",
                        progress_callback=_on_trans_progress,
                    )
                    translated_chunks = trans_result.get("speech_chunks") or trans_result.get("segments", [])

                    job_info["translation"] = {
                        "source_language": detected_lang,
                        "target_language": request.target_language,
                        "translation_style": request.translation_style,
                        "translated_chunks": len(translated_chunks),
                    }
                    await complete_stage(job_id, "translation", f"Dịch hoàn tất {len(translated_chunks)} SpeechChunks sang {request.target_language}")
                    # Tự động bảo đảm canonical SRT artifact ngay sau khi dịch xong (0 API call)
                    try:
                        await ensure_translated_srt_artifact(job_id, job_paths)
                    except Exception as e:
                        logger.warning(f"Không thể pre-generate SRT sau translation: {e}")
                else:
                    await start_stage(job_id, "translation", "Đang nạp bản dịch đã lưu...")
                    async with aiofiles.open(translated_path, "r", encoding="utf-8") as f:
                        cached_trans = json.loads(await f.read())
                        translated_chunks = cached_trans.get("speech_chunks", [])
                    await complete_stage(job_id, "translation", f"Tái sử dụng bản dịch {len(translated_chunks)} SpeechChunks đã có")
                    try:
                        await ensure_translated_srt_artifact(job_id, job_paths)
                    except Exception as e:
                        logger.warning(f"Không thể pre-generate SRT sau translation reuse: {e}")
            else:
                await skip_stage(job_id, "translation", "Bỏ qua dịch thuật")
        else:
            logger.info("[PIPELINE] stage=translation preserved from previous run (ZERO INVOCATION)")
            if translated_path.exists():
                async with aiofiles.open(translated_path, "r", encoding="utf-8") as f:
                    cached_trans = json.loads(await f.read())
                    translated_chunks = cached_trans.get("speech_chunks") or cached_trans.get("segments", [])
                try:
                    await ensure_translated_srt_artifact(job_id, job_paths)
                except Exception as e:
                    logger.warning(f"Không thể pre-generate SRT trong translation preserved: {e}")

        # -------------------------------------------------------------
        # STEP 4: AI Voice TTS (Edge-TTS Speech Generation with Continuity Analyzer)
        # -------------------------------------------------------------
        resolved_speed = resolve_effective_tts_speed(
            voice_id=request.voice_id,
            user_speed_rate=request.speed_rate or "+0%",
        )
        pause_profile = resolved_speed.get("pause_profile", "standard")
        effective_speed_str = resolved_speed.get("rate", request.speed_rate or "+0%")

        tts_input_chunks = translated_chunks if translated_chunks else speech_chunks

        # Phân tách Subtitle Segmentation khỏi TTS Speech Segmentation (Speech Continuity Analyzer)
        tts_phrases, continuity_debug = analyze_speech_continuity(
            speech_chunks=tts_input_chunks,
            style=request.translation_style or "movie_review_spoken_vi",
        )

        # Lưu log debug speech continuity
        continuity_debug_file = job_paths["transcript_dir"] / "speech_continuity_debug.json"
        try:
            continuity_debug_file.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(continuity_debug_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(continuity_debug, indent=2, ensure_ascii=False))
        except Exception as e:
            logger.warning(f"Lỗi ghi speech_continuity_debug.json: {e}")

        if "tts" in execution_plan:
            assert_stage_allowed("tts")
            current_running_stage = "tts"
            if needs_tts:
                existing_tts_count = 0
                for phrase in tts_phrases:
                    idx = phrase["index"]
                    seg_f = job_paths["tts_dir"] / f"segment_{idx:04d}.mp3"
                    if seg_f.exists() and seg_f.stat().st_size > 0:
                        existing_tts_count += 1

                total_tts_count = len(tts_phrases)
                initial_tts_pct = round((existing_tts_count / max(1, total_tts_count)) * 100.0, 1) if total_tts_count > 0 else 0.0
                initial_tts_msg = (
                    f"Đang tiếp tục tổng hợp {existing_tts_count}/{total_tts_count} TTS Phrases (Tái sử dụng {existing_tts_count} đoạn, {initial_tts_pct}%)"
                    if existing_tts_count > 0
                    else f"Đang tổng hợp giọng đọc AI ({request.voice_id})..."
                )

                await start_stage(job_id, "tts", initial_tts_msg, initial_progress=initial_tts_pct)

                async def _on_tts_progress(completed_count: int, total_count: int, message: Optional[str] = None, extra: Optional[Dict[str, Any]] = None):
                    pct = round((completed_count / max(1, total_count)) * 100.0, 1)
                    msg = message or f"Đang tổng hợp {completed_count}/{total_count} TTS Phrases ({pct}%)"
                    extra_data = {
                        "completed_chunks": completed_count,
                        "total_chunks": total_count,
                        "last_progress_at": _iso_now(),
                    }
                    if extra:
                        extra_data.update(extra)
                    await update_stage_progress(
                        job_id,
                        "tts",
                        progress=pct,
                        message=msg,
                        extra=extra_data,
                    )

                logger.info(f"[PIPELINE_EXEC] stage=tts service=generate_all_segments ({len(tts_phrases)} phrases)")
                tts_segments = await generate_all_segments(
                    segments=tts_phrases,
                    voice=request.voice_id,
                    tts_dir=job_paths["tts_dir"],
                    speed_rate=effective_speed_str,
                    progress_callback=_on_tts_progress,
                )
                await complete_stage(job_id, "tts", f"Tổng hợp thành công {len(tts_segments)} TTS Phrases liền mạch")
            else:
                await skip_stage(job_id, "tts", "Bỏ qua tổng hợp giọng đọc")
        else:
            logger.info("[PIPELINE] stage=tts preserved from previous run (ZERO INVOCATION)")
            try:
                tts_segments = reconstruct_tts_segments_from_disk(
                    tts_dir=job_paths["tts_dir"],
                    speech_chunks=tts_phrases,
                )
            except Exception as e:
                logger.warning(f"[PIPELINE] Could not pre-reconstruct tts_segments in tts preserved branch: {e}")

        # -------------------------------------------------------------
        # STEP 5: Audio Sync (Timeline Alignment & Natural Pauses)
        # -------------------------------------------------------------
        if "audio_sync" in execution_plan:
            assert_stage_allowed("audio_sync")
            current_running_stage = "audio_sync"
            if needs_tts:
                await start_stage(job_id, "audio_sync", f"Đang đồng bộ timeline và ghép track âm thanh 48kHz ({pause_profile})...")

                total_duration = float(job_info.get("video_info", {}).get("duration", 0.0))
                if total_duration <= 0:
                    v_probe = await probe_media_file(input_video_path)
                    total_duration = float(v_probe.get("duration", 0.0))

                temp_sync_dir = job_paths["tts_dir"] / "sync_temp"
                on_retry_cb, on_rec_cb = _make_retry_callbacks("audio_sync", "đồng bộ âm thanh")

                # Tái tạo tts_segments từ artifacts trên đĩa nếu tts đã được preserve (TEST F)
                if "tts_segments" not in locals() or not tts_segments:
                    logger.info("[PIPELINE] stage=audio_sync reconstructing tts_segments from disk artifacts...")
                    tts_segments = reconstruct_tts_segments_from_disk(
                        tts_dir=job_paths["tts_dir"],
                        speech_chunks=tts_input_chunks,
                    )

                # Validate input segments trước khi chạy (TEST B, E, G)
                validate_audio_sync_segments(tts_segments, verify_files_exist=True)

                async def _run_audio_sync_step():
                    return await sync_and_combine_voice_track(
                        tts_segments=tts_segments,
                        output_dubbed_wav=dubbed_voice_wav,
                        total_video_duration=total_duration,
                        temp_sync_dir=temp_sync_dir,
                        pause_profile=pause_profile,
                    )

                logger.info("[PIPELINE_EXEC] stage=audio_sync service=sync_and_combine_voice_track")
                raw_sync_res = await execute_with_auto_retry(
                    _run_audio_sync_step,
                    stage_name="audio_sync",
                    on_retry_callback=on_retry_cb,
                    on_recovered_callback=on_rec_cb,
                )
                dubbed_voice_wav, sync_stats = normalize_audio_sync_result(raw_sync_res)
                job_info["tts_result"] = sync_stats
                await complete_stage(job_id, "audio_sync", f"Đồng bộ hoàn tất (Timeline Drift: {sync_stats.get('timeline_drift_ms', 0.0):.1f}ms)")
            else:
                await skip_stage(job_id, "audio_sync", "Bỏ qua đồng bộ âm thanh")
        else:
            logger.info("[PIPELINE] stage=audio_sync preserved from previous run (ZERO INVOCATION)")
            sync_stats = job_info.get("tts_result", {})

        # -------------------------------------------------------------
        # STEP 6: Subtitles (.SRT & .ASS generation)
        # -------------------------------------------------------------
        if "subtitle" in execution_plan:
            assert_stage_allowed("subtitle")
            current_running_stage = "subtitle"
            if needs_subtitle:
                await start_stage(job_id, "subtitle", "Đang phân đoạn và validate phụ đề SRT & ASS...")
                chunks_for_subs = translated_chunks if translated_chunks else speech_chunks

                async def _generate_subtitles_step():
                    nonlocal valid_subs, subtitle_summary
                    _, valid_subs, subtitle_summary = await save_srt_file(chunks_for_subs, srt_file)
                    sub_style_dict = request.subtitle_style.dict() if request.subtitle_style else {}
                    await save_ass_file(valid_subs, ass_file, sub_style_dict)
                    return valid_subs, subtitle_summary

                on_retry_cb, on_rec_cb = _make_retry_callbacks("subtitle", "tạo phụ đề")
                logger.info("[PIPELINE_EXEC] stage=subtitle service=save_srt_file & save_ass_file")
                await execute_with_auto_retry(
                    _generate_subtitles_step,
                    stage_name="subtitle",
                    on_retry_callback=on_retry_cb,
                    on_recovered_callback=on_rec_cb,
                )

                job_info["subtitles_summary"] = subtitle_summary
                await complete_stage(job_id, "subtitle", f"Tạo file SRT & ASS thành công ({len(valid_subs)} phụ đề, Avg CPS: {subtitle_summary.get('average_cps', 0)})")
            else:
                await skip_stage(job_id, "subtitle", "Không tạo phụ đề")
        else:
            logger.info("[PIPELINE] stage=subtitle preserved from previous run (ZERO INVOCATION)")

        # -------------------------------------------------------------
        # STEP 7: Render Final Video
        # -------------------------------------------------------------
        if "render" in execution_plan:
            assert_stage_allowed("render")
            current_running_stage = "render"
            if needs_render:
                await start_stage(job_id, "render", f"Đang render video hoàn chỉnh ({request.output_resolution}, {request.output_format})...")

                on_retry_cb, on_rec_cb = _make_retry_callbacks("render", "render video")

                async def _run_render_step():
                    return await render_final_video(
                        input_video_path=input_video_path,
                        original_audio_path=original_audio_path,
                        dubbed_audio_path=dubbed_voice_wav,
                        output_video_path=output_final_mp4,
                        srt_subtitle_path=srt_file if (should_burn_subs and srt_file.exists()) else None,
                        ass_subtitle_path=ass_file if (should_burn_subs and ass_file.exists()) else None,
                        subtitle_style=request.subtitle_style.dict() if request.subtitle_style else None,
                        mask_regions=[m.dict() for m in request.mask_regions] if request.mask_regions else None,
                        keep_background_audio=request.keep_background_audio,
                        background_volume=request.background_volume,
                        voice_volume=request.voice_volume,
                        burn_subtitles=should_burn_subs,
                    )

                logger.info("[PIPELINE_EXEC] stage=render service=render_final_video")
                render_result = await execute_with_auto_retry(
                    _run_render_step,
                    stage_name="render",
                    on_retry_callback=on_retry_cb,
                    on_recovered_callback=on_rec_cb,
                )

                total_duration = float(job_info.get("video_info", {}).get("duration", 0.0))
                active_sync_stats = sync_stats if ('sync_stats' in locals() and isinstance(sync_stats, dict)) else (job_info.get("tts_result") if isinstance(job_info.get("tts_result"), dict) else {})
                pipeline_metrics = compute_pipeline_metrics(
                    speech_chunks=translated_chunks if translated_chunks else speech_chunks,
                    subtitles=valid_subs if 'valid_subs' in locals() and valid_subs else [],
                    sync_stats=active_sync_stats,
                    original_whisper_count=len(raw_segments),
                    expected_total_duration=total_duration,
                    synthesis_rate_percent=resolved_speed.get("synthesis_rate_percent", 0.0),
                )
                job_info["pipeline_metrics"] = pipeline_metrics
                job_info["render_result"] = render_result
                await complete_stage(job_id, "render", f"Render hoàn tất ({render_result.get('resolution')}, {format_file_size(render_result.get('size_bytes', 0))})")
            else:
                await skip_stage(job_id, "render", "Bỏ qua render video")
        else:
            logger.info("[PIPELINE] stage=render preserved from previous run (ZERO INVOCATION)")

        # Hoàn tất toàn bộ Pipeline thành công
        job_info = await load_job_info(job_id) or job_info
        job_info["status"] = "completed"
        job_info["progress"] = 100.0
        job_info["current_stage"] = None

        current_rev = job_info.get("output_revision", 0)
        new_output_rev = current_rev + 1 if needs_render else current_rev
        job_info["output_revision"] = new_output_rev

        final_video_url = f"/api/jobs/{job_id}/result/video?v={new_output_rev}" if (needs_render and output_final_mp4.exists()) else None
        download_video_url = f"/api/jobs/{job_id}/download/video?v={new_output_rev}" if (needs_render and output_final_mp4.exists()) else None
        download_srt_url = f"/api/jobs/{job_id}/download/subtitle?v={new_output_rev}" if srt_file.exists() else None

        active_segments = translated_chunks if translated_chunks else (speech_chunks if speech_chunks else raw_segments)
        job_info["segments"] = active_segments

        final_video_meta = {
            "available": bool(needs_render and output_final_mp4.exists() and output_final_mp4.stat().st_size > 0),
            "current": True,
            "reprocessing": False,
            "revision": new_output_rev,
            "filename": output_final_mp4.name if needs_render else None,
            "duration": render_result.get("duration"),
            "duration_formatted": render_result.get("duration_formatted"),
            "size": format_file_size(render_result.get("size_bytes", output_final_mp4.stat().st_size if output_final_mp4.exists() else 0)) if needs_render else None,
            "size_bytes": render_result.get("size_bytes", output_final_mp4.stat().st_size if output_final_mp4.exists() else 0) if needs_render else 0,
            "resolution": render_result.get("resolution"),
            "video_url": final_video_url,
            "download_video_url": download_video_url,
            "download_srt_url": download_srt_url,
            "video_codec": "h264",
            "audio_codec": "aac",
            "audio_sample_rate": 48000,
            "updated_at": _iso_now(),
            "config_signature": {
                "voice_id": request.voice_id,
                "speed_rate": request.speed_rate,
                "pitch": request.pitch,
                "translation_style": request.translation_style,
                "target_language": request.target_language,
                "output_resolution": request.output_resolution,
            },
        }

        job_info["video"] = final_video_meta
        artifacts = job_info.setdefault("artifacts", {})
        artifacts["final_video"] = final_video_meta
        artifacts["translation"] = {
            "available": bool(translated_chunks),
            "count": len(translated_chunks),
            "source_language": detected_lang,
            "target_language": request.target_language,
            "translation_style": request.translation_style,
        }
        artifacts["subtitles"] = {
            "available": srt_file.exists(),
            "download_srt_url": download_srt_url,
            "summary": subtitle_summary,
        }

        await save_job_info_atomic(job_id, job_info)

        return {
            "success": True,
            "message": "Xử lý pipeline hoàn tất thành công.",
            "job_id": job_id,
            "status": "completed",
            "progress": 100.0,
            "stages": job_info.get("stages", {}),
            "segments": active_segments,
            "video": final_video_meta,
            "artifacts": artifacts,
            "pipeline_metrics": pipeline_metrics if needs_render else None,
            "subtitle_validation": subtitle_summary,
        }

    except HTTPException as he:
        err_msg = str(he.detail) if hasattr(he, "detail") else str(he)
        logger.warning(f"HTTPException trong pipeline worker cho job {job_id}: {err_msg}")
        await fail_stage(job_id, current_running_stage, "HTTP_EXCEPTION", err_msg)
        return {"success": False, "job_id": job_id, "status": "failed", "error": err_msg}

    except AudioSyncError as ase:
        logger.error(f"Lỗi Audio Sync cho job {job_id}: {ase}", exc_info=True)
        await fail_stage(job_id, current_running_stage, ase.code, ase.message)
        return {"success": False, "job_id": job_id, "status": "failed", "error": ase.message, "error_code": ase.code}

    except Exception as e:
        logger.error(f"Lỗi khi thực thi Pipeline cho job {job_id} tại stage {current_running_stage}: {e}", exc_info=True)
        err_str = str(e)
        if is_fatal_api_key_error(e):
            err_str = "Khóa Gemini API không hợp lệ hoặc đã hết hạn (API_KEY_INVALID). Vui lòng bấm 'Thay đổi' tại mục Cấu hình dịch thuật để nhập API Key mới và thử lại."
            err_code = "API_KEY_INVALID"
        elif isinstance(e, AttributeError):
            err_str = f"Lỗi cấu trúc dữ liệu nội bộ ({current_running_stage}): {e}"
            err_code = "INTERNAL_DATA_STRUCTURE_ERROR"
        else:
            err_code = "PIPELINE_ERROR"

        await fail_stage(job_id, current_running_stage, err_code, err_str)
        return {"success": False, "job_id": job_id, "status": "failed", "error": err_str}

    finally:
        unregister_active_task(job_id)

