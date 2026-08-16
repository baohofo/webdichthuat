import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.config import (
    ATEMPO_ACCEPTABLE_MAX,
    ATEMPO_HARD_MAX,
    ATEMPO_NORMAL_MAX,
    SUBTITLE_MAX_CPS,
    SUBTITLE_WARN_OVER_DURATION,
    SUBTITLE_WARN_UNDER_DURATION,
)

logger = logging.getLogger("validation_service")


def compute_pipeline_metrics(
    speech_chunks: List[Dict[str, Any]],
    subtitles: List[Dict[str, Any]],
    sync_stats: Dict[str, Any],
    original_whisper_count: int = 0,
    expected_total_duration: float = 0.0,
    synthesis_rate_percent: float = 0.0,
) -> Dict[str, Any]:
    """
    Tính toán và đánh giá bộ chỉ số kiểm định chất lượng toàn diện của pipeline AI Dubbing:
    - Đo lường cấu trúc SpeechChunk & Subtitles
    - Đo lường Pause Profile & khoảng nghỉ thở tự nhiên
    - Đo lường Multi-layer Speed: Edge-TTS synthesis rate + FFmpeg sync atempo factor + Final cumulative speed estimate
    """
    total_chunks = len(speech_chunks)
    total_subs = len(subtitles)

    # 1. Đo lường SpeechChunk
    chunk_durations = [float(c.get("duration", 0.0)) for c in speech_chunks if "duration" in c]
    avg_chunk_dur = round(sum(chunk_durations) / max(1, total_chunks), 2) if total_chunks else 0.0
    short_chunk_count = sum(1 for d in chunk_durations if d < 2.0)
    merged_whisper_count = max(0, original_whisper_count - total_chunks)

    # 2. Đo lường Subtitle
    sub_durations = [float(s.get("duration", 0.0)) for s in subtitles if "duration" in s]
    avg_sub_dur = round(sum(sub_durations) / max(1, total_subs), 2) if total_subs else 0.0

    cps_list = [float(s.get("cps", 0.0)) for s in subtitles if "cps" in s]
    avg_cps = round(sum(cps_list) / max(1, total_subs), 2) if total_subs else 0.0
    max_cps = round(max(cps_list), 2) if cps_list else 0.0

    sub_under_08s = sum(1 for s in subtitles if float(s.get("duration", 0.0)) < SUBTITLE_WARN_UNDER_DURATION)
    sub_over_6s = sum(1 for s in subtitles if float(s.get("duration", 0.0)) > SUBTITLE_WARN_OVER_DURATION)
    sub_over_22_cps = sum(1 for s in subtitles if float(s.get("cps", 0.0)) > SUBTITLE_MAX_CPS)

    # 3. Đo lường Pause Profile & Khoảng lặng
    pauses = [float(p) for p in sync_stats.get("pauses", []) if p > 0.0]
    avg_pause_dur = round(sum(pauses) / max(1, len(pauses)), 3) if pauses else 0.0
    long_pause_count = sum(1 for p in pauses if p > 0.8)

    # 4. Đo lường atempo & Multi-layer Effective Speed
    speedups = [float(sp) for sp in sync_stats.get("speedups", [])]
    if not speedups:
        speedups = [1.0]

    speedup_1_00_to_1_15 = sum(1 for sp in speedups if sp <= ATEMPO_NORMAL_MAX)
    speedup_1_15_to_1_25 = sum(1 for sp in speedups if ATEMPO_NORMAL_MAX < sp <= ATEMPO_ACCEPTABLE_MAX)
    speedup_1_25_to_1_40 = sum(1 for sp in speedups if ATEMPO_ACCEPTABLE_MAX < sp <= ATEMPO_HARD_MAX)
    speedup_over_1_40 = sum(1 for sp in speedups if sp > ATEMPO_HARD_MAX)

    speed_over_1_15_count = sum(1 for sp in speedups if sp > 1.15)
    speed_over_1_25_count = sum(1 for sp in speedups if sp > 1.25)
    speed_over_1_40_count = sum(1 for sp in speedups if sp > 1.40)

    avg_atempo_factor = round(sum(speedups) / max(1, len(speedups)), 3)
    max_atempo_factor = round(max(speedups), 3)

    # Synthesis speed rate (ví dụ: +15% -> factor 1.15)
    synth_rate = float(sync_stats.get("synthesis_rate_percent", synthesis_rate_percent))
    synth_factor = 1.0 + (synth_rate / 100.0)

    # Tốc độ hiệu dụng cuối cùng (Cumulative Effective Speed)
    avg_effective_speed = round(synth_factor * avg_atempo_factor, 3)
    max_effective_speed = round(synth_factor * max_atempo_factor, 3)

    timeline_drift_ms = round(float(sync_stats.get("timeline_drift_ms", 0.0)), 2)
    max_timeline_drift_ms = round(float(sync_stats.get("max_timeline_drift_ms", 0.0)), 2)
    overlap_count = int(sync_stats.get("overlap_count", 0))

    # Đánh giá mức độ đạt chuẩn
    is_acceptable = (
        (speedup_over_1_40 == 0)
        and (speedup_1_25_to_1_40 <= max(3, int(total_chunks * 0.15)))
        and (max_timeline_drift_ms <= 1500.0)  # Drift không quá 1.5 giây
        and (max_effective_speed <= 1.65)      # Tránh gắt / quá nhanh tổng thể
        and (avg_cps <= 26.0)                  # Ngưỡng CPS trung bình an toàn cho fast speech
    )

    metrics = {
        "valid": is_acceptable,
        "total_speech_chunks": total_chunks,
        "original_whisper_count": original_whisper_count,
        "merged_whisper_segments": merged_whisper_count,
        "subtitle_count": total_subs,
        # SpeechChunk metrics
        "average_speech_chunk_duration": avg_chunk_dur,
        "average_tts_chunk_duration": avg_chunk_dur,
        "short_speech_chunk_count": short_chunk_count,
        # Pause metrics
        "pause_profile": sync_stats.get("pause_profile", "standard"),
        "average_pause_duration": avg_pause_dur,
        "long_pause_count": long_pause_count,
        # Subtitle metrics
        "average_subtitle_duration": avg_sub_dur,
        "average_cps": avg_cps,
        "max_cps": max_cps,
        "subtitle_under_0_8s": sub_under_08s,
        "subtitle_over_6s": sub_over_6s,
        "subtitle_over_22_cps": sub_over_22_cps,
        # Multi-layer Speed & atempo metrics
        "synthesis_rate_percent": synth_rate,
        "sync_atempo_factor": avg_atempo_factor,
        "final_effective_speed_estimate": avg_effective_speed,
        "average_effective_speed": avg_effective_speed,
        "max_effective_speed": max_effective_speed,
        "speed_over_1_15_count": speed_over_1_15_count,
        "speed_over_1_25_count": speed_over_1_25_count,
        "speed_over_1_40_count": speed_over_1_40_count,
        "speedup_1_00_to_1_15": speedup_1_00_to_1_15,
        "speedup_1_15_to_1_25": speedup_1_15_to_1_25,
        "speedup_1_25_to_1_40": speedup_1_25_to_1_40,
        "speedup_over_1_40_clamped": speedup_over_1_40,
        "translation_recompression_count": int(sync_stats.get("translation_recompression_count", 0)),
        "tts_regeneration_count": int(sync_stats.get("tts_regeneration_count", 0)),
        # Timeline drift & Overlap
        "overlap_count": overlap_count,
        "timeline_drift_ms": timeline_drift_ms,
        "max_timeline_drift_ms": max_timeline_drift_ms,
    }

    logger.info(
        f"================= PIPELINE VALIDATION METRICS ================="
    )
    logger.info(f"Chunks: {total_chunks} (Avg dur: {avg_chunk_dur}s, Short <2s: {short_chunk_count})")
    logger.info(f"Subtitles: {total_subs} | Avg CPS: {avg_cps} | Max CPS: {max_cps}")
    logger.info(f"Pauses: Profile='{sync_stats.get('pause_profile', 'standard')}' | Avg: {avg_pause_dur}s | Long >0.8s: {long_pause_count}")
    logger.info(
        f"Speed: Synth: {synth_rate:+}% | Sync atempo: {avg_atempo_factor}x | Final Effective: {avg_effective_speed}x (Max: {max_effective_speed}x)"
    )
    logger.info(
        f"Atempo distribution: [<=1.15x: {speedup_1_00_to_1_15}] [1.15-1.25x: {speedup_1_15_to_1_25}] "
        f"[1.25-1.40x: {speedup_1_25_to_1_40}] [>1.40x clamped: {speedup_over_1_40}]"
    )
    logger.info(f"Timeline Drift: {timeline_drift_ms}ms (Max: {max_timeline_drift_ms}ms)")
    logger.info(f"Overall Status: {'PASSED ✓' if is_acceptable else 'WARNING ⚠️'}")
    logger.info("===============================================================")

    return metrics

