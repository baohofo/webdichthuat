import logging
from pathlib import Path
from typing import Any, Dict, Tuple
from backend.config import (
    FINAL_AUDIO_CHANNELS,
    FINAL_AUDIO_SAMPLE_RATE,
    WHISPER_AUDIO_CHANNELS,
    WHISPER_AUDIO_SAMPLE_RATE,
)
from backend.utils.ffmpeg_utils import probe_media_file, run_command_async

logger = logging.getLogger("video_service")


async def get_video_info(video_path: Path) -> Dict[str, Any]:
    """
    Lấy thông tin chi tiết và kiểm tra tính hợp lệ của file video tải lên.
    """
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    info = await probe_media_file(video_path)
    return info


async def extract_dual_audio(
    video_path: Path,
    audio_dir: Path,
) -> Dict[str, Any]:
    """
    Trích xuất đồng thời 2 file âm thanh riêng biệt:
    1. 'original_audio.wav': 48,000 Hz, Stereo (2 channels), PCM 16-bit -> Dùng cho Mix & Render video chất lượng cao.
    2. 'whisper.wav': 16,000 Hz, Mono (1 channel), PCM 16-bit -> CHỈ dùng riêng cho mô hình Faster-Whisper STT.
    """
    if not video_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file video: {video_path}")

    video_info = await get_video_info(video_path)
    if not video_info.get("has_audio"):
        raise ValueError(
            f"Video '{video_path.name}' không có luồng âm thanh (Audio Stream). Vui lòng chọn video có tiếng để xử lý."
        )

    audio_dir.mkdir(parents=True, exist_ok=True)
    original_audio_path = audio_dir / "original_audio.wav"
    whisper_audio_path = audio_dir / "whisper.wav"

    # Lệnh trích xuất đồng thời 2 luồng qua FFmpeg filter graph (tiết kiệm thời gian đọc video)
    # Output 1: 48kHz Stereo PCM (Original Background)
    # Output 2: 16kHz Mono PCM (Whisper STT)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path.resolve()),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", str(FINAL_AUDIO_SAMPLE_RATE),
        "-ac", str(FINAL_AUDIO_CHANNELS),
        str(original_audio_path.resolve()),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", str(WHISPER_AUDIO_SAMPLE_RATE),
        "-ac", str(WHISPER_AUDIO_CHANNELS),
        str(whisper_audio_path.resolve()),
    ]

    logger.info(f"Đang trích xuất Dual Audio từ video {video_path.name}...")
    returncode, _, stderr = await run_command_async(cmd, timeout=600)

    if returncode != 0:
        logger.error(f"FFmpeg dual audio extraction failed: {stderr}")
        raise RuntimeError(f"Trích xuất âm thanh thất bại: {stderr.strip()}")

    if not original_audio_path.exists() or original_audio_path.stat().st_size == 0:
        raise RuntimeError("Trích xuất original_audio.wav thất bại.")
    if not whisper_audio_path.exists() or whisper_audio_path.stat().st_size == 0:
        raise RuntimeError("Trích xuất whisper.wav thất bại.")

    orig_info = await probe_media_file(original_audio_path)
    whisper_info = await probe_media_file(whisper_audio_path)

    logger.info(
        f"✓ Đã trích xuất thành công:\n"
        f"  - Original Audio (Mix): {original_audio_path.name} ({orig_info.get('audio_sample_rate')} Hz, {orig_info.get('audio_channels')} ch, {orig_info.get('size_bytes')} bytes)\n"
        f"  - Whisper Audio (STT): {whisper_audio_path.name} ({whisper_info.get('audio_sample_rate')} Hz, {whisper_info.get('audio_channels')} ch, {whisper_info.get('size_bytes')} bytes)"
    )

    return {
        "original_audio_path": str(original_audio_path),
        "whisper_audio_path": str(whisper_audio_path),
        "filename": original_audio_path.name,
        "duration": orig_info.get("duration"),
        "duration_formatted": orig_info.get("duration_formatted"),
        "size_bytes": orig_info.get("size_bytes"),
        "sample_rate": orig_info.get("audio_sample_rate"),
        "channels": orig_info.get("audio_channels"),
    }


async def extract_audio_to_wav(
    video_path: Path,
    output_wav_path: Path,
    sample_rate: int = 16000,
    channels: int = 1,
) -> Dict[str, Any]:
    """
    Hàm tương thích ngược phục vụ trích xuất đơn lẻ nếu cần.
    """
    if not video_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file video: {video_path}")

    output_wav_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path.resolve()),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", str(sample_rate),
        "-ac", str(channels),
        str(output_wav_path.resolve())
    ]
    returncode, _, stderr = await run_command_async(cmd, timeout=600)
    if returncode != 0:
        raise RuntimeError(f"Trích xuất thất bại: {stderr}")

    info = await probe_media_file(output_wav_path)
    return {
        "audio_path": str(output_wav_path),
        "filename": output_wav_path.name,
        "duration": info.get("duration"),
        "duration_formatted": info.get("duration_formatted"),
        "size_bytes": info.get("size_bytes"),
        "sample_rate": info.get("audio_sample_rate"),
        "channels": info.get("audio_channels"),
    }
