import asyncio
import json
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
    MOVIE_REVIEW_PAUSE_CAP,
    MOVIE_REVIEW_PAUSE_COLON_SEMICOLON,
    MOVIE_REVIEW_PAUSE_COMMA,
    MOVIE_REVIEW_PAUSE_DRAMATIC,
    MOVIE_REVIEW_PAUSE_ELLIPSIS,
    MOVIE_REVIEW_PAUSE_SENTENCE_END,
    MOVIE_REVIEW_PAUSE_TRANSITION,
    PAUSE_COLON_SEMICOLON,
    PAUSE_COMMA,
    PAUSE_ELLIPSIS,
    PAUSE_PROFILES,
    PAUSE_SENTENCE_END,
)
from backend.services.speech_chunk_service import is_ellipsis_ending
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
      - Dấu ba chấm lửng (… / ...): 0.35s
      - Dấu kết câu (. ! ?): 0.32s
      - Dấu hai chấm, chấm phẩy (: ;): 0.22s
      - Dấu phẩy, gạch ngang (, — -): 0.15s
    - Movie Review Profile:
      - Dấu ba chấm lửng (… / ...): 0.25s (0.20–0.35s MAX)
      - Dấu kết câu (. ! ?): 0.22s (0.18–0.28s)
      - Dấu hai chấm, chấm phẩy (: ;): 0.15s (0.12–0.18s)
      - Dấu phẩy, gạch ngang (, — -): 0.10s (0.08–0.12s)
    """
    clean = text.strip()
    is_ellipsis = clean.endswith("...") or clean.endswith("…") or punctuation_hint in {"…", "..."} or is_ellipsis_ending(clean)
    last_char = clean[-1] if clean else punctuation_hint

    if pause_profile == "movie_review":
        if is_ellipsis:
            return MOVIE_REVIEW_PAUSE_ELLIPSIS
        if last_char in {".", "!", "?"}:
            return MOVIE_REVIEW_PAUSE_SENTENCE_END
        if last_char in {":", ";"}:
            return MOVIE_REVIEW_PAUSE_COLON_SEMICOLON
        if last_char in {",", "—", "-"}:
            return MOVIE_REVIEW_PAUSE_COMMA
        return MOVIE_REVIEW_PAUSE_COMMA
    else:
        if is_ellipsis:
            return PAUSE_ELLIPSIS
        if last_char in {".", "!", "?"}:
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


class AudioSyncError(RuntimeError):
    """Lỗi định dạng hoặc dữ liệu trong Audio Sync stage."""
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def validate_audio_sync_segments(
    tts_segments: Any,
    verify_files_exist: bool = True,
) -> List[Dict[str, Any]]:
    """
    Validate chặt chẽ schema đầu vào của audio_sync (Requirement 7):
    - tts_segments phải là List[Dict[str, Any]].
    - Mỗi segment phải có index, start, end, file_path.
    - Nếu verify_files_exist = True, file_path phải tồn tại trên đĩa và size >= MIN_VALID_AUDIO_BYTES.
    Nếu sai format, ném AudioSyncError với code AUDIO_SYNC_INVALID_SEGMENT_SCHEMA hoặc AUDIO_SYNC_MISSING_TTS_ARTIFACT.
    """
    from backend.config import MIN_VALID_AUDIO_BYTES

    if not isinstance(tts_segments, list):
        logger.error(f"[AUDIO_SYNC_SCHEMA_MISMATCH] expected=list actual={type(tts_segments).__name__}")
        raise AudioSyncError(
            "AUDIO_SYNC_INVALID_SEGMENT_SCHEMA",
            f"Dữ liệu đầu vào của Audio Sync phải là danh sách (List), nhận được: {type(tts_segments).__name__}"
        )

    validated = []
    for idx, seg in enumerate(tts_segments):
        if not isinstance(seg, dict):
            logger.error(f"[AUDIO_SYNC_SCHEMA_MISMATCH] item_idx={idx} expected=dict actual={type(seg).__name__}")
            raise AudioSyncError(
                "AUDIO_SYNC_INVALID_SEGMENT_SCHEMA",
                f"Segment #{idx} không phải là Dictionary (nhận được {type(seg).__name__})."
            )

        if "start" not in seg or "end" not in seg:
            raise AudioSyncError(
                "AUDIO_SYNC_INVALID_SEGMENT_SCHEMA",
                f"Segment #{seg.get('index', idx)} thiếu thông tin start hoặc end timeline."
            )

        try:
            start_val = float(seg["start"])
            end_val = float(seg["end"])
        except (ValueError, TypeError) as e:
            raise AudioSyncError(
                "AUDIO_SYNC_INVALID_SEGMENT_SCHEMA",
                f"Segment #{seg.get('index', idx)} có start/end không phải số hợp lệ: {e}"
            )

        file_path_str = seg.get("file_path")
        if not file_path_str:
            raise AudioSyncError(
                "AUDIO_SYNC_MISSING_TTS_ARTIFACT",
                f"Segment #{seg.get('index', idx)} thiếu đường dẫn file_path âm thanh."
            )

        file_p = Path(file_path_str)
        if verify_files_exist:
            if not file_p.exists() or file_p.stat().st_size < MIN_VALID_AUDIO_BYTES:
                raise AudioSyncError(
                    "AUDIO_SYNC_MISSING_TTS_ARTIFACT",
                    f"File âm thanh của chunk #{seg.get('index', idx)} không tồn tại hoặc bị hỏng trên đĩa: {file_p.name}"
                )

        validated.append(seg)

    return validated


def normalize_audio_sync_result(result: Any) -> Tuple[Path, Dict[str, Any]]:
    """
    Adapter chuẩn hóa đầu ra của sync_and_combine_voice_track (Requirement 6):
    - Hỗ trợ tuple (Path, dict)
    - Hỗ trợ dict {"output_audio_path": ..., ...}
    - Đảm bảo trả về đúng tuple (Path, Dict[str, Any])
    """
    if isinstance(result, tuple) and len(result) == 2:
        out_path, stats = result
        return Path(out_path), dict(stats) if isinstance(stats, dict) else {}
    elif isinstance(result, dict):
        out_path = Path(result.get("output_audio_path") or result.get("dubbed_voice_wav") or "")
        return out_path, result
    elif isinstance(result, (str, Path)):
        return Path(result), {}

    raise AudioSyncError(
        "AUDIO_SYNC_INVALID_RESULT",
        f"Kết quả Audio Sync không đúng chuẩn (nhận được {type(result).__name__})."
    )


def reconstruct_tts_segments_from_disk(
    tts_dir: Path,
    speech_chunks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Tái tạo danh sách tts_segments từ artifacts trên đĩa khi resume từ audio_sync (TEST F & G):
    - Đọc từ tts_chunks_state.json và các file segment_*.mp3
    - Bảo toàn 100% metadata start, end, file_path
    - Kiểm tra tính đầy đủ của file artifacts
    """
    from backend.config import MIN_VALID_AUDIO_BYTES

    if not speech_chunks:
        return []

    checkpoint_file = tts_dir / "tts_chunks_state.json"
    chunk_map = {}
    if checkpoint_file.exists():
        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                chunk_map = json.load(f)
        except Exception:
            chunk_map = {}

    reconstructed = []
    for seg in speech_chunks:
        idx = seg["index"]
        seg_file = tts_dir / f"segment_{idx:04d}.mp3"
        if not seg_file.exists() or seg_file.stat().st_size < MIN_VALID_AUDIO_BYTES:
            raise AudioSyncError(
                "AUDIO_SYNC_MISSING_TTS_ARTIFACT",
                f"Thiếu file audio segment_{idx:04d}.mp3 trên đĩa cho SpeechChunk #{idx}."
            )

        seg_start = float(seg.get("start", 0.0))
        seg_end = float(seg.get("end", seg_start + 2.0))
        seg_dur = float(seg.get("duration", round(seg_end - seg_start, 2)))

        reconstructed.append({
            "index": idx,
            "phrase_id": seg.get("phrase_id", idx),
            "start": seg_start,
            "end": seg_end,
            "duration": seg_dur,
            "text": (seg.get("translated_text") or seg.get("original_text") or "").strip(),
            "display_text": seg.get("display_text") or (seg.get("translated_text") or seg.get("original_text") or "").strip(),
            "spoken_text": seg.get("spoken_text") or (seg.get("translated_text") or seg.get("original_text") or "").strip(),
            "file_path": str(seg_file),
            "punctuation_end": seg.get("punctuation_end", ""),
            "is_complete_sentence": seg.get("is_complete_sentence", False),
            "original_text": seg.get("original_text", ""),
            "original_whisper_indices": seg.get("original_whisper_indices", []),
            "source_chunks": seg.get("source_chunks", [idx]),
            "member_count": seg.get("member_count", 1),
            "reused": True,
        })

    return reconstructed


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
    - Single Gap Fill: Điều phối khoảng cách giữa các câu chính xác theo timeline video thực tế, không tạo duplicate silence segments.
    - Thu thập toàn bộ chỉ số speedups, pauses, timeline drift, overlap và diagnostics chi tiết cho từng SpeechChunk.
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
        "chunk_diagnostics": [],
        "long_pause_count": 0,
        "max_pause_duration": 0.0,
        "average_pause_duration": 0.0,
    }

    if not tts_segments:
        silence_path = await create_silence_wav(output_dubbed_wav, total_video_duration)
        return silence_path, sync_stats

    # Validate input segments
    validated_segs = validate_audio_sync_segments(tts_segments, verify_files_exist=True)
    existing_artifacts_count = sum(1 for s in validated_segs if Path(s.get("file_path", "")).exists())

    logger.info(
        f"[AUDIO_SYNC_START] Bắt đầu đồng bộ và ghép {len(validated_segs)} câu lồng tiếng 48kHz Stereo "
        f"({total_video_duration:.2f}s, pause_profile='{pause_profile}', "
        f"existing_artifacts={existing_artifacts_count}/{len(validated_segs)}, "
        f"first_item_schema={list(validated_segs[0].keys()) if validated_segs else []})..."
    )

    sorted_segs = sorted(validated_segs, key=lambda s: float(s["start"]))
    concat_files: List[Path] = []
    current_timeline_pos = 0.0
    max_drift_ms = 0.0
    overlap_count = 0
    long_pause_count = 0

    for idx, seg in enumerate(sorted_segs):
        start_time = float(seg["start"])
        end_time = float(seg["end"])
        target_dur = max(0.4, end_time - start_time)
        raw_audio_path = Path(seg["file_path"])

        if not raw_audio_path.exists():
            continue

        # 1. Bù khoảng lặng đầu tiên nếu audio chưa bắt đầu tại start_time (chỉ áp dụng ở đầu timeline)
        if start_time > current_timeline_pos + 0.02:
            silence_dur = start_time - current_timeline_pos
            silence_file = temp_sync_dir / f"lead_silence_{idx:04d}.wav"
            await create_silence_wav(silence_file, silence_dur)
            concat_files.append(silence_file)
            current_timeline_pos += silence_dur
            sync_stats["pauses"].append(round(silence_dur, 3))
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

        # 3. Tính toán khoảng cách tới câu tiếp theo
        if idx + 1 < len(sorted_segs):
            next_start = float(sorted_segs[idx + 1]["start"])
        else:
            next_start = total_video_duration

        available_gap = max(0.0, next_start - current_timeline_pos)

        # Lấy khoảng nghỉ chuẩn theo dấu câu và pause_profile
        seg_text = seg.get("text", "")
        punct = seg.get("punctuation_end", "")
        desired_pause = get_natural_pause_duration(seg_text, punct, pause_profile=pause_profile)

        # Cảnh báo chất lượng nếu khoảng nghỉ trong câu review liên tục quá dài (> 0.6s)
        if pause_profile == "movie_review" and available_gap > 0.60:
            long_pause_count += 1
            logger.warning(
                f"[QUALITY_WARNING] Chunk #{seg.get('index', idx+1)} có khoảng nghỉ lớn "
                f"({available_gap:.2f}s > 0.6s) trong phong cách review phim."
            )

        # Chèn duy nhất một file pause chuẩn cho toàn bộ available_gap
        if available_gap > 0.02:
            pause_file = temp_sync_dir / f"pause_{idx:04d}.wav"
            await create_silence_wav(pause_file, available_gap)
            concat_files.append(pause_file)
            current_timeline_pos += available_gap
            sync_stats["pauses"].append(round(available_gap, 3))

        # Thu thập diagnostics chi tiết cho từng SpeechChunk
        orig_gap = max(0.0, next_start - end_time) if idx + 1 < len(sorted_segs) else 0.0
        sync_stats["chunk_diagnostics"].append({
            "chunk_id": int(seg.get("index", idx + 1)),
            "display_text": seg.get("display_text") or seg.get("text", ""),
            "tts_text": seg.get("spoken_text") or seg.get("text", ""),
            "slot_duration": round(target_dur, 2),
            "tts_duration": round(seg_actual_dur, 2),
            "original_gap": round(orig_gap, 2),
            "punctuation_type": punct if punct else ("…" if is_ellipsis_ending(seg_text) else "none"),
            "semantic_pause": round(desired_pause, 2),
            "final_pause": round(available_gap, 2) if available_gap > 0.02 else 0.0,
            "effective_speed": applied_speed,
        })

    # 4. Chèn khoảng lặng ở cuối video nếu timeline chưa đạt đến tổng độ dài video
    if total_video_duration > current_timeline_pos + 0.05:
        trailing_dur = total_video_duration - current_timeline_pos
        trailing_silence = temp_sync_dir / "silence_trailing.wav"
        await create_silence_wav(trailing_silence, trailing_dur)
        concat_files.append(trailing_silence)
        current_timeline_pos += trailing_dur
        sync_stats["pauses"].append(round(trailing_dur, 3))

    final_drift_ms = abs(current_timeline_pos - total_video_duration) * 1000.0
    sync_stats["timeline_drift_ms"] = final_drift_ms
    sync_stats["max_timeline_drift_ms"] = max_drift_ms
    sync_stats["overlap_count"] = overlap_count
    sync_stats["long_pause_count"] = long_pause_count

    all_pauses = [p for p in sync_stats["pauses"] if p > 0.0]
    sync_stats["max_pause_duration"] = round(max(all_pauses), 3) if all_pauses else 0.0
    sync_stats["average_pause_duration"] = round(sum(all_pauses) / len(all_pauses), 3) if all_pauses else 0.0

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

