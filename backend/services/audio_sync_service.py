import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import aiofiles

from backend.config import (
    ATEMPO_ACCEPTABLE_MAX,
    ATEMPO_HARD_MAX,
    ATEMPO_NORMAL_MAX,
    FINAL_AUDIO_CHANNELS,
    FINAL_AUDIO_SAMPLE_RATE,
    MOVIE_REVIEW_PAUSE_COLON_SEMICOLON,
    MOVIE_REVIEW_PAUSE_COMMA,
    MOVIE_REVIEW_PAUSE_DRAMATIC,
    MOVIE_REVIEW_PAUSE_SENTENCE_END,
    MOVIE_REVIEW_PAUSE_TRANSITION,
    PAUSE_COLON_SEMICOLON,
    PAUSE_COMMA,
    PAUSE_PROFILES,
    PAUSE_SENTENCE_END,
)
from backend.utils.ffmpeg_utils import probe_media_file, run_command_async

logger = logging.getLogger("audio_sync_service")


def get_natural_pause_duration(
    text: str,
    punctuation_hint: str = "",
    pause_profile: str = "standard",
) -> float:
    """
    Tính khoảng nghỉ tự nhiên chuẩn xác theo từng profile (Deterministic Natural Pause):
    - Standard Profile:
      - Dấu kết câu (. ! ? …): 0.32s
      - Dấu hai chấm, chấm phẩy (: ;): 0.22s
      - Dấu phẩy, gạch ngang (, — -): 0.15s
    - Movie Review Profile:
      - Dấu kết câu (. ! ? …): 0.25s (nhanh, dứt khoát, liền mạch)
      - Dấu hai chấm, chấm phẩy (: ;): 0.16s
      - Dấu phẩy, gạch ngang (, — -): 0.10s
    """
    clean = text.strip()
    last_char = clean[-1] if clean else punctuation_hint

    if pause_profile == "movie_review":
        if last_char in {".", "!", "?", "…"}:
            return MOVIE_REVIEW_PAUSE_SENTENCE_END
        if last_char in {":", ";"}:
            return MOVIE_REVIEW_PAUSE_COLON_SEMICOLON
        if last_char in {",", "—", "-"}:
            return MOVIE_REVIEW_PAUSE_COMMA
        return MOVIE_REVIEW_PAUSE_COMMA
    else:
        if last_char in {".", "!", "?", "…"}:
            return PAUSE_SENTENCE_END
        if last_char in {":", ";"}:
            return PAUSE_COLON_SEMICOLON
        if last_char in {",", "—", "-"}:
            return PAUSE_COMMA
        return PAUSE_COMMA


def build_atempo_filter(speed: float) -> str:
    """
    Xây dựng chuỗi bộ lọc atempo hợp lệ của FFmpeg (mỗi bộ lọc nằm trong khoảng 0.5 đến 2.0).
    Ví dụ: speed = 2.5 -> 'atempo=2.0,atempo=1.25'
    """
    filters = []
    current = max(0.25, min(4.0, speed))

    while current > 2.0:
        filters.append("atempo=2.0")
        current /= 2.0
    while current < 0.5:
        filters.append("atempo=0.5")
        current /= 0.5

    filters.append(f"atempo={current:.3f}")
    return ",".join(filters)


async def adjust_audio_speed_if_needed(
    input_audio: Path,
    output_audio: Path,
    target_duration: float,
    sample_rate: int = FINAL_AUDIO_SAMPLE_RATE,
    channels: int = FINAL_AUDIO_CHANNELS,
) -> Tuple[float, float]:
    """
    Điều chỉnh tốc độ âm thanh theo chính sách atempo phân cấp:
    - required_speed <= 1.05x: Giữ nguyên tốc độ (1.0x)
    - 1.05x < required_speed <= 1.15x: Bình thường (Optimal)
    - 1.15x < required_speed <= 1.25x: Chấp nhận khi cần (Acceptable)
    - 1.25x < required_speed <= 1.40x: Cảnh báo / Emergency only
    - required_speed > 1.40x: Clamp cứng tại 1.40x để tránh méo giọng
    Trả về: (actual_duration, applied_speed)
    """
    output_audio.parent.mkdir(parents=True, exist_ok=True)
    audio_info = await probe_media_file(input_audio)
    actual_duration = float(audio_info.get("duration", 0.0))

    if target_duration <= 0.1:
        target_duration = actual_duration

    # Tính toán tốc độ cần thiết để khớp thời lượng
    required_speed = actual_duration / max(0.4, target_duration)

    if required_speed <= 1.05:
        speed = 1.0
        filter_args = []
    elif required_speed <= ATEMPO_NORMAL_MAX:
        speed = round(required_speed, 2)
        filter_args = ["-filter:a", build_atempo_filter(speed)]
        logger.info(f"TTS_SPEEDUP_OPTIMAL: Tăng tốc {input_audio.name}: {actual_duration:.2f}s -> {target_duration:.2f}s ({speed}x)")
    elif required_speed <= ATEMPO_ACCEPTABLE_MAX:
        speed = round(required_speed, 2)
        filter_args = ["-filter:a", build_atempo_filter(speed)]
        logger.info(f"TTS_SPEEDUP_ACCEPTABLE: Câu dài {input_audio.name} tăng tốc {speed}x (mức chấp nhận)")
    elif required_speed <= ATEMPO_HARD_MAX:
        speed = round(required_speed, 2)
        filter_args = ["-filter:a", build_atempo_filter(speed)]
        logger.warning(
            f"TTS_SPEEDUP_EMERGENCY: Câu dài {input_audio.name} tăng tốc {speed}x (vượt 1.25x, dưới hạn 1.40x)"
        )
    else:
        speed = ATEMPO_HARD_MAX
        filter_args = ["-filter:a", build_atempo_filter(speed)]
        logger.warning(
            f"TTS_DURATION_OVERFLOW: Câu thoại {input_audio.name} cần tốc độ {required_speed:.2f}x (> {ATEMPO_HARD_MAX}x). "
            f"Tự động clamp tại {speed}x để bảo toàn chất lượng âm thanh."
        )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_audio.resolve()),
    ]
    cmd.extend(filter_args)
    cmd.extend([
        "-ar", str(sample_rate),
        "-ac", str(channels),
        "-acodec", "pcm_s16le",
        str(output_audio.resolve())
    ])

    ret, _, err = await run_command_async(cmd, timeout=60)
    if ret != 0:
        logger.error(f"Lỗi xử lý audio speed: {err}")
        raise RuntimeError(f"Lỗi xử lý âm thanh đoạn: {err}")

    adjusted_info = await probe_media_file(output_audio)
    res_dur = float(adjusted_info.get("duration", actual_duration))
    return res_dur, speed


async def create_silence_wav(
    output_wav: Path,
    duration: float,
    sample_rate: int = FINAL_AUDIO_SAMPLE_RATE,
    channels: int = FINAL_AUDIO_CHANNELS,
) -> Path:
    """
    Tạo một đoạn âm thanh im lặng (Silence) chuẩn 48,000 Hz Stereo siêu nhanh bằng Python wave module.
    """
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    safe_dur = max(0.01, duration)
    num_frames = int(sample_rate * safe_dur)
    
    import wave
    with wave.open(str(output_wav.resolve()), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit PCM (2 bytes per sample)
        wf.setframerate(sample_rate)
        # Ghi các sample 0 (silence)
        wf.writeframes(b"\x00" * (num_frames * channels * 2))

    return output_wav


async def sync_and_combine_voice_track(
    tts_segments: List[Dict[str, Any]],
    output_dubbed_wav: Path,
    total_video_duration: float,
    temp_sync_dir: Path,
    pause_profile: str = "standard",
) -> Tuple[Path, Dict[str, Any]]:
    """
    Đồng bộ toàn bộ các câu thoại TTS vào đúng timeline video với Natural Pause Model:
    - Bắt đầu chính xác tại speech.start.
    - Chèn khoảng nghỉ thở tự nhiên dựa trên dấu câu kết thúc và pause_profile (standard / movie_review).
    - Clamp khoảng nghỉ theo available_gap để triệt tiêu hoàn toàn Timeline Drift.
    - Thu thập toàn bộ chỉ số speedups, pauses, timeline drift và overlap.
    """
    output_dubbed_wav.parent.mkdir(parents=True, exist_ok=True)
    temp_sync_dir.mkdir(parents=True, exist_ok=True)

    sync_stats: Dict[str, Any] = {
        "speedups": [],
        "pauses": [],
        "pause_profile": pause_profile,
        "timeline_drift_ms": 0.0,
        "max_timeline_drift_ms": 0.0,
        "overlap_count": 0,
    }

    if not tts_segments:
        silence_path = await create_silence_wav(output_dubbed_wav, total_video_duration)
        return silence_path, sync_stats

    logger.info(
        f"Bắt đầu đồng bộ và ghép {len(tts_segments)} câu lồng tiếng 48kHz Stereo vào timeline "
        f"({total_video_duration:.2f}s, pause_profile='{pause_profile}')..."
    )

    sorted_segs = sorted(tts_segments, key=lambda s: float(s["start"]))
    concat_files: List[Path] = []
    current_timeline_pos = 0.0
    max_drift_ms = 0.0
    overlap_count = 0

    for idx, seg in enumerate(sorted_segs):
        start_time = float(seg["start"])
        end_time = float(seg["end"])
        target_dur = max(0.4, end_time - start_time)
        raw_audio_path = Path(seg["file_path"])

        if not raw_audio_path.exists():
            continue

        # 1. Chèn khoảng lặng trước câu nói nếu có khoảng cách (Bảo toàn Original Speech Rhythm)
        if start_time > current_timeline_pos + 0.02:
            silence_dur = start_time - current_timeline_pos
            silence_file = temp_sync_dir / f"silence_{idx:04d}.wav"
            await create_silence_wav(silence_file, silence_dur)
            concat_files.append(silence_file)
            current_timeline_pos += silence_dur
            sync_stats["pauses"].append(silence_dur)
        elif current_timeline_pos > start_time + 0.05:
            # Overlap do câu trước kéo dài hơn start của câu này
            overlap_count += 1

        # 2. Điều chỉnh tốc độ câu thoại (chuẩn hóa 48kHz Stereo)
        adj_file = temp_sync_dir / f"adjusted_{idx:04d}.wav"
        seg_actual_dur, applied_speed = await adjust_audio_speed_if_needed(raw_audio_path, adj_file, target_dur)
        concat_files.append(adj_file)
        current_timeline_pos += seg_actual_dur
        sync_stats["speedups"].append(applied_speed)

        # Đo timeline drift tại mốc kết thúc câu
        drift_ms = abs(current_timeline_pos - end_time) * 1000.0
        if drift_ms > max_drift_ms:
            max_drift_ms = drift_ms

        # 3. Tính toán khoảng nghỉ thở tự nhiên (Deterministic Natural Pause Model)
        if idx + 1 < len(sorted_segs):
            next_start = float(sorted_segs[idx + 1]["start"])
        else:
            next_start = total_video_duration

        available_gap = next_start - current_timeline_pos

        # Lấy khoảng nghỉ chuẩn theo dấu câu và pause_profile
        seg_text = seg.get("text", "")
        punct = seg.get("punctuation_end", "")
        desired_pause = get_natural_pause_duration(seg_text, punct, pause_profile=pause_profile)

        # Clamp theo available_gap để KHÔNG BAO GIỜ drift sang câu sau
        dynamic_pause = max(0.0, min(desired_pause, available_gap))

        if dynamic_pause > 0.02:
            pause_file = temp_sync_dir / f"pause_{idx:04d}.wav"
            await create_silence_wav(pause_file, dynamic_pause)
            concat_files.append(pause_file)
            current_timeline_pos += dynamic_pause
            sync_stats["pauses"].append(dynamic_pause)

    # 4. Chèn khoảng lặng ở cuối video nếu timeline chưa đạt đến tổng độ dài video
    if total_video_duration > current_timeline_pos + 0.05:
        trailing_dur = total_video_duration - current_timeline_pos
        trailing_silence = temp_sync_dir / "silence_trailing.wav"
        await create_silence_wav(trailing_silence, trailing_dur)
        concat_files.append(trailing_silence)
        current_timeline_pos += trailing_dur
        sync_stats["pauses"].append(trailing_dur)

    final_drift_ms = abs(current_timeline_pos - total_video_duration) * 1000.0
    sync_stats["timeline_drift_ms"] = final_drift_ms
    sync_stats["max_timeline_drift_ms"] = max_drift_ms
    sync_stats["overlap_count"] = overlap_count

    # 5. Tạo file danh sách concat cho FFmpeg
    concat_list_file = temp_sync_dir / "concat_list.txt"
    lines = [f"file '{f.resolve().as_posix()}'" for f in concat_files]

    async with aiofiles.open(concat_list_file, "w", encoding="utf-8") as f:
        await f.write("\n".join(lines))

    # 6. Ghép nối các file thành một track 48,000 Hz Stereo hoàn chỉnh
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_file.resolve()),
        "-c:a", "pcm_s16le",
        "-ar", str(FINAL_AUDIO_SAMPLE_RATE),
        "-ac", str(FINAL_AUDIO_CHANNELS),
        str(output_dubbed_wav.resolve())
    ]

    ret, _, err = await run_command_async(cmd_concat, timeout=300)
    if ret != 0:
        logger.error(f"Lỗi khi ghép track audio lồng tiếng: {err}")
        raise RuntimeError(f"Lỗi ghép audio lồng tiếng: {err}")

    dub_info = await probe_media_file(output_dubbed_wav)
    logger.info(
        f"✓ Đã tạo thành công track lồng tiếng: {output_dubbed_wav.name} "
        f"({dub_info.get('audio_sample_rate')} Hz, {dub_info.get('audio_channels')} ch, duration: {dub_info.get('duration_formatted')})"
    )
    return output_dubbed_wav, sync_stats

