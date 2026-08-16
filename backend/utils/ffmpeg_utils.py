import asyncio
import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("ffmpeg_utils")


def is_ffmpeg_available() -> bool:
    """
    Kiểm tra xem FFmpeg và FFprobe đã được cài đặt và có trong PATH chưa.
    """
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def check_ffmpeg_installed() -> Tuple[bool, str]:
    """
    Kiểm tra FFmpeg và trả về trạng thái kèm thông điệp.
    """
    ok = is_ffmpeg_available()
    msg = "FFmpeg & FFprobe đã sẵn sàng." if ok else "Không tìm thấy FFmpeg/FFprobe trong PATH."
    return ok, msg



def _run_subprocess_sync(cmd_args: List[str], timeout: Optional[int] = 300) -> Tuple[int, str, str]:
    """
    Thực thi lệnh bằng subprocess chuẩn đồng bộ (an toàn tuyệt đối trên Windows).
    """
    cmd_str = " ".join(cmd_args)
    logger.info(f"Executing: {cmd_str}")

    try:
        res = subprocess.run(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        stdout = res.stdout.decode("utf-8", errors="replace")
        stderr = res.stderr.decode("utf-8", errors="replace")
        return res.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout}s: {cmd_str}")
        raise TimeoutError(f"Quá thời gian xử lý ({timeout} giây): {cmd_str}")
    except FileNotFoundError as e:
        logger.error(f"Binary not found: {cmd_args[0]}")
        raise RuntimeError(
            f"Không tìm thấy công cụ '{cmd_args[0]}'. Hãy đảm bảo FFmpeg đã được cài đặt và thêm vào PATH."
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error running {cmd_args[0]}: {e}")
        raise


async def run_command_async(
    cmd_args: List[str], timeout: Optional[int] = 300
) -> Tuple[int, str, str]:
    """
    Chạy lệnh FFmpeg/FFprobe bất đồng bộ thông qua thread pool, tránh lỗi ProactorPipeTransport trên Windows.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _run_subprocess_sync, cmd_args, timeout)


async def probe_media_file(file_path: Path) -> Dict[str, Any]:
    """
    Sử dụng ffprobe để lấy thông tin chi tiết của video/audio (Duration, Resolution, Audio Streams...).
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File không tồn tại: {file_path}")

    # Đường dẫn tuyệt đối chuẩn hóa cho Windows
    resolved_path = str(file_path.resolve())

    cmd = [
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        resolved_path
    ]

    returncode, stdout, stderr = await run_command_async(cmd, timeout=60)
    if returncode != 0:
        err_msg = stderr.strip() or f"FFprobe trả về mã lỗi {returncode}"
        logger.error(f"FFprobe error on {file_path}: {err_msg}")
        raise RuntimeError(f"Lỗi khi phân tích thông số video: {err_msg}")

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse ffprobe JSON. stdout: {stdout[:500]}, stderr: {stderr}")
        raise RuntimeError("Không thể đọc định dạng thông tin video từ ffprobe") from e

    format_info = data.get("format", {})
    streams = data.get("streams", [])

    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    duration = float(format_info.get("duration", 0.0))
    if duration == 0.0 and video_streams:
        duration = float(video_streams[0].get("duration", 0.0))
    if duration == 0.0 and audio_streams:
        duration = float(audio_streams[0].get("duration", 0.0))

    width = int(video_streams[0].get("width", 0)) if video_streams else 0
    height = int(video_streams[0].get("height", 0)) if video_streams else 0

    return {
        "filename": file_path.name,
        "duration": duration,
        "duration_formatted": f"{int(duration // 60):02d}:{int(duration % 60):02d}",
        "size_bytes": int(format_info.get("size", file_path.stat().st_size)),
        "bit_rate": int(format_info.get("bit_rate", 0)),
        "has_video": len(video_streams) > 0,
        "has_audio": len(audio_streams) > 0,
        "video_codec": video_streams[0].get("codec_name") if video_streams else None,
        "audio_codec": audio_streams[0].get("codec_name") if audio_streams else None,
        "resolution": f"{width}x{height}" if width and height else "Unknown",
        "audio_channels": int(audio_streams[0].get("channels", 0)) if audio_streams else 0,
        "audio_sample_rate": int(audio_streams[0].get("sample_rate", 0)) if audio_streams else 0,
    }
