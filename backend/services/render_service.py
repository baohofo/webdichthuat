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


def build_video_filter_graph(
    mask_regions: Optional[List[Dict[str, Any]]],
    burn_subtitles: bool,
    ass_subtitle_path: Optional[Path],
    srt_subtitle_path: Optional[Path],
    subtitle_style: Optional[Dict[str, Any]],
    video_width: int = 1920,
    video_height: int = 1080,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Xây dựng chuỗi Video Filter graph đa tầng:
    Input [0:v] -> Vùng che / Blur (Mask Layer, z=10) -> Subtitle Burn (Subtitle Layer, z=20) -> [vout]
    Bảo đảm bất biến: Subtitle luôn nằm trên Mask và không bao giờ bị blur.
    """
    active_masks = [m for m in (mask_regions or []) if m.get("enabled", True)]
    has_sub = burn_subtitles and ((ass_subtitle_path and ass_subtitle_path.exists()) or (srt_subtitle_path and srt_subtitle_path.exists()))

    if not active_masks and not has_sub:
        return None, None

    v_filters = []
    cur_label = "0:v"

    # 1. Áp dụng từng Mask / Blur region (Mask Layer)
    for i, m in enumerate(active_masks):
        raw_x = max(0.0, min(1.0, float(m.get("x", 0.10))))
        raw_y = max(0.0, min(1.0, float(m.get("y", 0.75))))
        raw_w = max(0.02, min(1.0 - raw_x, float(m.get("width", 0.80))))
        raw_h = max(0.02, min(1.0 - raw_y, float(m.get("height", 0.15))))

        w_box = max(2, int(round(raw_w * video_width)))
        h_box = max(2, int(round(raw_h * video_height)))
        # Đảm bảo kích thước chẵn cho bộ mã hóa YUV420p
        w_box = w_box - (w_box % 2)
        h_box = h_box - (h_box % 2)

        x_px = min(int(round(raw_x * video_width)), max(0, video_width - w_box))
        y_px = min(int(round(raw_y * video_height)), max(0, video_height - h_box))

        mask_type = m.get("type", "blur")
        if mask_type == "solid":
            color_hex = str(m.get("color", "#000000")).replace("#", "0x")
            opacity = max(0.0, min(1.0, float(m.get("opacity", 0.85))))
            next_label = f"v_mask_{i}"
            v_filters.append(f"[{cur_label}]drawbox=x={x_px}:y={y_px}:w={w_box}:h={h_box}:color={color_hex}@{opacity:.2f}:t=fill[{next_label}]")
            cur_label = next_label
        else:
            # Blur region
            strength = max(1, min(30, int(m.get("blur_strength", 15))))
            luma_rad = max(2, min(40, strength * 2))
            split_base = f"v_base_{i}"
            split_crop = f"v_crop_{i}"
            v_blur = f"v_blur_{i}"
            next_label = f"v_mask_{i}"

            v_filters.append(f"[{cur_label}]split=2[{split_base}][{split_crop}]")
            v_filters.append(f"[{split_crop}]crop={w_box}:{h_box}:{x_px}:{y_px},boxblur=luma_radius={luma_rad}:luma_power=2[{v_blur}]")
            v_filters.append(f"[{split_base}][{v_blur}]overlay={x_px}:{y_px}[{next_label}]")
            cur_label = next_label

    # 2. Khắc phụ đề Subtitle Burn (Subtitle Layer - LUÔN nằm trên Mask)
    if has_sub:
        if ass_subtitle_path and ass_subtitle_path.exists():
            ass_posix = ass_subtitle_path.resolve().as_posix().replace(":", "\\:")
            v_filters.append(f"[{cur_label}]ass='{ass_posix}'[vout]")
            cur_label = "vout"
        elif srt_subtitle_path and srt_subtitle_path.exists():
            srt_posix = srt_subtitle_path.resolve().as_posix().replace(":", "\\:")
            v_filters.append(f"[{cur_label}]subtitles='{srt_posix}'[vout]")
            cur_label = "vout"
    else:
        if v_filters:
            v_filters.append(f"[{cur_label}]null[vout]")
            cur_label = "vout"

    return ";".join(v_filters), cur_label


async def render_final_video(
    input_video_path: Path,
    original_audio_path: Optional[Path],
    dubbed_audio_path: Path,
    output_video_path: Path,
    srt_subtitle_path: Optional[Path] = None,
    ass_subtitle_path: Optional[Path] = None,
    subtitle_style: Optional[Dict[str, Any]] = None,
    mask_regions: Optional[List[Dict[str, Any]]] = None,
    keep_background_audio: bool = True,
    background_volume: float = 0.15,
    voice_volume: float = 1.0,
    burn_subtitles: bool = False,
) -> Dict[str, Any]:
    """
    Kết hợp Video gốc + Mask/Blur Regions + Phụ đề ASS/SRT + AI Voice Track (48kHz) + Background Audio (48kHz).
    - Áp dụng Mask Layer trước, Subtitle Burn sau (Z-order chuẩn).
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
    video_w = int(video_info.get("width") or 1920)
    video_h = int(video_info.get("height") or 1080)

    logger.info(
        f"Bắt đầu render video 48kHz Stereo: {output_video_path.name} "
        f"(burn_subs={burn_subtitles}, masks={len(mask_regions or [])}, keep_bg={keep_background_audio}, bg_vol={background_volume:.2f}, voice_vol={voice_volume:.2f})"
    )

    cmd = ["ffmpeg", "-y"]

    # 1. Inputs
    cmd.extend(["-i", str(input_video_path.resolve())])          # Input 0: Video gốc
    cmd.extend(["-i", str(dubbed_audio_path.resolve())])         # Input 1: AI Dubbed Voice (48kHz)

    has_bg = keep_background_audio and original_audio_path and original_audio_path.exists() and background_volume > 0.001
    if has_bg:
        cmd.extend(["-i", str(original_audio_path.resolve())])   # Input 2: Original Audio (48kHz)

    # 2. Xử lý Video Filter Graph (Mask Layer -> Subtitle Layer)
    video_filter_str, vout_label = build_video_filter_graph(
        mask_regions=mask_regions,
        burn_subtitles=burn_subtitles,
        ass_subtitle_path=ass_subtitle_path,
        srt_subtitle_path=srt_subtitle_path,
        subtitle_style=subtitle_style,
        video_width=video_w,
        video_height=video_h,
    )

    # 3. Xử lý Audio Filter (Mix 48kHz + Loudness Normalization chống clipping)
    if has_bg:
        audio_filter_str = (
            f"[2:a]volume={background_volume:.2f}[bg];"
            f"[1:a]volume={voice_volume:.2f}[dub];"
            f"[bg][dub]amix=inputs=2:duration=first:dropout_transition=2[mixed];"
            f"[mixed]loudnorm=I=-16:TP=-1.5:LRA=11[aout]"
        )
    else:
        audio_filter_str = (
            f"[1:a]volume={voice_volume:.2f}[dub];"
            f"[dub]loudnorm=I=-16:TP=-1.5:LRA=11[aout]"
        )

    # 4. Tổ hợp Filter Complex
    if video_filter_str:
        combined_filter = f"{video_filter_str};{audio_filter_str}"
        codec_args = [
            "-filter_complex", combined_filter,
            "-map", f"[{vout_label}]",
            "-map", "[aout]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
        ]
    else:
        # Không có mask và không burn sub -> Stream copy video
        codec_args = [
            "-filter_complex", audio_filter_str,
            "-map", "0:v:0",
            "-map", "[aout]",
            "-c:v", "copy",
        ]

    audio_codec_args = [
        "-c:a", FINAL_AUDIO_CODEC,
        "-b:a", FINAL_AUDIO_BITRATE,
        "-ar", str(FINAL_AUDIO_SAMPLE_RATE),
        "-ac", str(FINAL_AUDIO_CHANNELS),
    ]

    # 5. Gộp toàn bộ lệnh FFmpeg render ra file staging tạm (.processing.mp4)
    staging_video_path = output_video_path.with_name(f"{output_video_path.stem}.processing{output_video_path.suffix}")
    if staging_video_path.exists():
        staging_video_path.unlink(missing_ok=True)

    cmd.extend(codec_args)
    cmd.extend(audio_codec_args)
    cmd.append(str(staging_video_path.resolve()))

    timeout = 600 if (burn_subtitles or video_filter_str) else 240
    ret, _, err = await run_command_async(cmd, timeout=timeout)

    if ret != 0:
        if staging_video_path.exists():
            staging_video_path.unlink(missing_ok=True)
        logger.error(f"Render video thất bại: {err}")
        raise RuntimeError(f"Lỗi khi render video hoàn chỉnh: {err}")

    # Hậu kiểm chất lượng video và audio trên file staging trước khi commit
    try:
        validation = await validate_final_render(staging_video_path, expected_duration)
    except Exception as ve:
        if staging_video_path.exists():
            staging_video_path.unlink(missing_ok=True)
        raise ve

    # Atomic replace file staging sang output_video_path chính thức
    import os, shutil
    for attempt in range(5):
        try:
            os.replace(str(staging_video_path), str(output_video_path))
            break
        except (PermissionError, OSError):
            if attempt == 4:
                shutil.copy2(str(staging_video_path), str(output_video_path))
                staging_video_path.unlink(missing_ok=True)
            else:
                await asyncio.sleep(0.05 * (attempt + 1))

    return {
        "output_video_path": str(output_video_path),
        "filename": output_video_path.name,
        "duration": validation.get("duration"),
        "duration_formatted": validation.get("duration_formatted"),
        "size_bytes": validation.get("size_bytes"),
        "resolution": validation.get("resolution"),
        "validation": validation,
    }
