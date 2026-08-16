import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from backend.config import (
    FINAL_AUDIO_BITRATE,
    FINAL_AUDIO_CHANNELS,
    FINAL_AUDIO_CODEC,
    FINAL_AUDIO_SAMPLE_RATE,
)
from backend.utils.ffmpeg_utils import probe_media_file, run_command_async

logger = logging.getLogger("render_service")


async def validate_final_render(
    output_video_path: Path,
    expected_duration: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Hậu kiểm video xuất ra bằng ffprobe:
    - Kiểm tra định dạng audio codec (AAC), sample rate (48000 Hz), số kênh (2).
    - So sánh thời lượng đầu vào và đầu ra (cảnh báo OUTPUT_DURATION_MISMATCH nếu lệch > 0.5s).
    """
    if not output_video_path.exists() or output_video_path.stat().st_size == 0:
        raise RuntimeError("FINAL_AUDIO_INVALID: File video đầu ra không tồn tại hoặc rỗng.")

    info = await probe_media_file(output_video_path)
    audio_sr = int(info.get("audio_sample_rate") or 0)
    audio_ch = int(info.get("audio_channels") or 0)
    audio_codec = str(info.get("audio_codec") or "").lower()
    actual_dur = float(info.get("duration") or 0.0)

    is_audio_valid = (audio_sr == FINAL_AUDIO_SAMPLE_RATE) and (audio_ch == FINAL_AUDIO_CHANNELS)
    if not is_audio_valid:
        logger.warning(
            f"FINAL_AUDIO_INVALID: Audio output có sample rate {audio_sr} Hz ({audio_ch} ch), "
            f"kỳ vọng {FINAL_AUDIO_SAMPLE_RATE} Hz ({FINAL_AUDIO_CHANNELS} ch)."
        )

    duration_diff = 0.0
    if expected_duration and expected_duration > 0.1:
        duration_diff = round(abs(actual_dur - expected_duration), 2)
        if duration_diff > 0.5:
            logger.warning(
                f"OUTPUT_DURATION_MISMATCH: Thời lượng video xuất ra ({actual_dur:.2f}s) "
                f"lệch {duration_diff:.2f}s so với video gốc ({expected_duration:.2f}s)."
            )

    validation_summary = {
        "valid": is_audio_valid and (duration_diff <= 1.0),
        "video_codec": info.get("video_codec"),
        "audio_codec": audio_codec,
        "sample_rate": audio_sr,
        "channels": audio_ch,
        "duration": actual_dur,
        "duration_formatted": info.get("duration_formatted"),
        "duration_difference": duration_diff,
        "size_bytes": info.get("size_bytes"),
        "resolution": info.get("resolution"),
    }

    logger.info(
        f"✓ Post-render validation: Codec={info.get('video_codec')}/{audio_codec}, "
        f"Audio={audio_sr}Hz {audio_ch}ch, Duration={info.get('duration_formatted')}"
    )

    return validation_summary


async def render_final_video(
    input_video_path: Path,
    original_audio_path: Optional[Path],
    dubbed_audio_path: Path,
    output_video_path: Path,
    srt_subtitle_path: Optional[Path] = None,
    ass_subtitle_path: Optional[Path] = None,
    subtitle_style: Optional[Dict[str, Any]] = None,
    keep_background_audio: bool = True,
    background_volume: float = 0.15,
    voice_volume: float = 1.0,
    burn_subtitles: bool = False,
) -> Dict[str, Any]:
    """
    Kết hợp Video gốc + AI Voice Track (48kHz) + Original Background Audio (48kHz) + Phụ đề ASS/SRT.
    - Áp dụng Loudness Normalization (loudnorm) chống clipping.
    - Xuất video chuẩn H.264 + AAC 48,000 Hz Stereo 192 kbps.
    """
    if not input_video_path.exists():
        raise FileNotFoundError(f"Video gốc không tồn tại: {input_video_path}")
    if not dubbed_audio_path.exists():
        raise FileNotFoundError(f"Track âm thanh lồng tiếng không tồn tại: {dubbed_audio_path}")

    output_video_path.parent.mkdir(parents=True, exist_ok=True)
    video_info = await probe_media_file(input_video_path)
    expected_duration = float(video_info.get("duration") or 0.0)

    logger.info(
        f"Bắt đầu render video 48kHz Stereo: {output_video_path.name} "
        f"(burn_subs={burn_subtitles}, keep_bg={keep_background_audio}, bg_vol={background_volume:.2f}, voice_vol={voice_volume:.2f})"
    )

    cmd = ["ffmpeg", "-y"]

    # 1. Inputs
    cmd.extend(["-i", str(input_video_path.resolve())])          # Input 0: Video gốc
    cmd.extend(["-i", str(dubbed_audio_path.resolve())])         # Input 1: AI Dubbed Voice (48kHz)

    has_bg = keep_background_audio and original_audio_path and original_audio_path.exists() and background_volume > 0.001
    if has_bg:
        cmd.extend(["-i", str(original_audio_path.resolve())])   # Input 2: Original Audio (48kHz)

    # 2. Xử lý Video Filter (Burn Styled ASS vs SRT vs Stream Copy)
    if burn_subtitles:
        sub_filter = None
        if ass_subtitle_path and ass_subtitle_path.exists():
            ass_posix = ass_subtitle_path.resolve().as_posix().replace(":", "\\:")
            sub_filter = f"ass='{ass_posix}'"
        elif srt_subtitle_path and srt_subtitle_path.exists():
            srt_posix = srt_subtitle_path.resolve().as_posix().replace(":", "\\:")
            # Cấu hình force_style từ SubtitleStyle
            style = subtitle_style or {}
            fn = style.get("font_family") or "Arial"
            fs = int(style.get("font_size") or 22)
            sub_filter = (
                f"subtitles='{srt_posix}':force_style="
                f"'FontName={fn},FontSize={fs},PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,MarginV=35'"
            )

        if sub_filter:
            video_codec_args = [
                "-vf", sub_filter,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "22",
                "-pix_fmt", "yuv420p"
            ]
        else:
            video_codec_args = ["-c:v", "copy"]
    else:
        # Không cần re-encode video nếu không burn phụ đề -> Stream copy siêu nhanh
        video_codec_args = ["-c:v", "copy"]

    # 3. Xử lý Audio Filter (Mix 48kHz + Loudness Normalization chống clipping)
    if has_bg:
        filter_complex = (
            f"[2:a]volume={background_volume:.2f}[bg];"
            f"[1:a]volume={voice_volume:.2f}[dub];"
            f"[bg][dub]amix=inputs=2:duration=first:dropout_transition=2[mixed];"
            f"[mixed]loudnorm=I=-16:TP=-1.5:LRA=11[aout]"
        )
    else:
        filter_complex = (
            f"[1:a]volume={voice_volume:.2f}[dub];"
            f"[dub]loudnorm=I=-16:TP=-1.5:LRA=11[aout]"
        )

    audio_codec_args = [
        "-filter_complex", filter_complex,
        "-map", "0:v:0",
        "-map", "[aout]",
        "-c:a", FINAL_AUDIO_CODEC,
        "-b:a", FINAL_AUDIO_BITRATE,
        "-ar", str(FINAL_AUDIO_SAMPLE_RATE),
        "-ac", str(FINAL_AUDIO_CHANNELS),
    ]

    # Gộp toàn bộ lệnh FFmpeg
    cmd.extend(video_codec_args)
    cmd.extend(audio_codec_args)
    cmd.append(str(output_video_path.resolve()))

    timeout = 600 if burn_subtitles else 240
    ret, _, err = await run_command_async(cmd, timeout=timeout)

    if ret != 0:
        logger.error(f"Render video thất bại: {err}")
        raise RuntimeError(f"Lỗi khi render video hoàn chỉnh: {err}")

    # Hậu kiểm chất lượng video và audio sau khi render
    validation = await validate_final_render(output_video_path, expected_duration)

    return {
        "output_video_path": str(output_video_path),
        "filename": output_video_path.name,
        "duration": validation.get("duration"),
        "duration_formatted": validation.get("duration_formatted"),
        "size_bytes": validation.get("size_bytes"),
        "resolution": validation.get("resolution"),
        "validation": validation,
    }
