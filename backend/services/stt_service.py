import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import aiofiles
from faster_whisper import WhisperModel
import ctranslate2

logger = logging.getLogger("stt_service")

# Bộ nhớ đệm lưu trữ các mô hình đã tải để tránh tải lại nhiều lần
_LOADED_MODELS: Dict[str, WhisperModel] = {}
_FALLBACK_TO_CPU = False


def get_whisper_model(model_size: str = "small", force_cpu: bool = False) -> WhisperModel:
    """
    Khởi tạo hoặc lấy mô hình Whisper từ bộ nhớ đệm (Cache).
    Tự động thử CUDA nếu có GPU, nếu thiếu DLL (cublas) sẽ tự động fallback sang CPU int8 mượt mà.
    """
    global _FALLBACK_TO_CPU
    valid_models = {"tiny", "base", "small", "medium", "large-v3"}
    if model_size not in valid_models:
        raise ValueError(f"INVALID_WHISPER_MODEL: Mô hình '{model_size}' không hợp lệ. Các model hỗ trợ: {', '.join(sorted(valid_models))}")

    cache_key = f"{model_size}_cpu" if (force_cpu or _FALLBACK_TO_CPU) else f"{model_size}_auto"

    if cache_key in _LOADED_MODELS:
        return _LOADED_MODELS[cache_key]

    if force_cpu or _FALLBACK_TO_CPU:
        logger.info(f"Đang nạp mô hình Faster-Whisper '{model_size}' trên CPU (int8)...")
        model = WhisperModel(
            model_size_or_path=model_size,
            device="cpu",
            compute_type="int8",
            download_root=None,
        )
    else:
        has_cuda = ctranslate2.get_cuda_device_count() > 0
        device = "cuda" if has_cuda else "cpu"
        compute_type = "default" if has_cuda else "int8"
        logger.info(f"Đang nạp mô hình Faster-Whisper '{model_size}' trên device '{device}'...")

        try:
            model = WhisperModel(
                model_size_or_path=model_size,
                device=device,
                compute_type=compute_type,
                download_root=None,
            )
        except Exception as e:
            logger.warning(f"Không thể khởi tạo trên device '{device}' ({e}), chuyển sang fallback 'cpu'")
            _FALLBACK_TO_CPU = True
            cache_key = f"{model_size}_cpu"
            model = WhisperModel(
                model_size_or_path=model_size,
                device="cpu",
                compute_type="int8",
            )

    _LOADED_MODELS[cache_key] = model
    logger.info(f"Nạp thành công mô hình Faster-Whisper '{model_size}' ({cache_key})")
    return model


def _run_transcription_sync(
    audio_path: str,
    model_size: str,
    language: Optional[str] = None,
    progress_sync_callback: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Hàm thực thi nhận diện giọng nói đồng bộ trong worker thread.
    BẬT word_timestamps=True để bóc tách timestamp từng từ phục vụ Subtitle Segmenter.
    Cập nhật tiến độ % thời gian thực theo từng segment nhận diện được.
    """
    global _FALLBACK_TO_CPU
    lang_param = None if (not language or language.lower() in ["auto", "none", ""]) else language.lower()

    try:
        model = get_whisper_model(model_size)
        segments_generator, info = model.transcribe(
            audio_path,
            language=lang_param,
            beam_size=5,
            word_timestamps=True,  # BẬT WORD TIMESTAMPS
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )
        total_duration = max(0.1, float(info.duration)) if info and hasattr(info, "duration") else 0.1
        raw_segments = []
        for seg in segments_generator:
            raw_segments.append(seg)
            if progress_sync_callback and total_duration > 0:
                pct = min(99.0, round((seg.end / total_duration) * 100.0, 1))
                try:
                    progress_sync_callback(pct, f"Đang nhận dạng {seg.end:.1f}s / {total_duration:.1f}s ({pct}%)")
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"Lỗi khi chạy Whisper trên device hiện tại ({e}), tự động chuyển sang chạy trên CPU...")
        _FALLBACK_TO_CPU = True
        model = get_whisper_model(model_size, force_cpu=True)
        segments_generator, info = model.transcribe(
            audio_path,
            language=lang_param,
            beam_size=5,
            word_timestamps=True,  # BẬT WORD TIMESTAMPS
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )
        total_duration = max(0.1, float(info.duration)) if info and hasattr(info, "duration") else 0.1
        raw_segments = []
        for seg in segments_generator:
            raw_segments.append(seg)
            if progress_sync_callback and total_duration > 0:
                pct = min(99.0, round((seg.end / total_duration) * 100.0, 1))
                try:
                    progress_sync_callback(pct, f"Đang nhận dạng {seg.end:.1f}s / {total_duration:.1f}s ({pct}%)")
                except Exception:
                    pass

    detected_language = info.language
    language_probability = round(info.language_probability, 4)
    duration = round(info.duration, 2)

    segments_list: List[Dict[str, Any]] = []
    index = 1

    for segment in raw_segments:
        text = segment.text.strip()
        if not text:
            continue

        start_time = round(segment.start, 2)
        end_time = round(segment.end, 2)
        seg_duration = round(end_time - start_time, 2)

        # Trích xuất chi tiết từng từ
        words_data: List[Dict[str, Any]] = []
        if hasattr(segment, "words") and segment.words:
            for w in segment.words:
                w_text = (w.word or "").strip()
                if w_text:
                    words_data.append({
                        "word": w_text,
                        "start": round(w.start, 2),
                        "end": round(w.end, 2),
                        "probability": round(getattr(w, "probability", 1.0), 4),
                    })

        segments_list.append({
            "index": index,
            "start": start_time,
            "end": end_time,
            "duration": seg_duration,
            "original_text": text,
            "translated_text": "",
            "words": words_data,
            "no_speech_prob": round(getattr(segment, "no_speech_prob", 0.0), 4),
        })
        index += 1

    logger.info(
        f"Hoàn thành STT cho {audio_path}: {len(segments_list)} segments nhận diện được "
        f"(Word timestamps: {'Bật' if any(s['words'] for s in segments_list) else 'Trống'}). "
        f"Ngôn ngữ: {detected_language} ({language_probability * 100:.1f}%)"
    )

    return {
        "detected_language": detected_language,
        "language_probability": language_probability,
        "duration": duration,
        "total_segments": len(segments_list),
        "segments": segments_list,
    }


async def transcribe_audio(
    audio_path: Path,
    output_transcript_path: Path,
    model_size: str = "small",
    language: Optional[str] = None,
    progress_callback: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Nhận diện giọng nói từ file audio WAV (whisper.wav) và xuất ra file JSON transcript có word timestamps.
    Hỗ trợ progress_callback bất đồng bộ / đồng bộ.
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file audio: {audio_path}")

    output_transcript_path.parent.mkdir(parents=True, exist_ok=True)

    loop = asyncio.get_running_loop()

    def _sync_progress_bridge(pct: float, msg: str):
        if progress_callback:
            if asyncio.iscoroutinefunction(progress_callback):
                asyncio.run_coroutine_threadsafe(progress_callback(pct, msg), loop)
            else:
                loop.call_soon_threadsafe(progress_callback, pct, msg)

    result = await loop.run_in_executor(
        None,
        _run_transcription_sync,
        str(audio_path.resolve()),
        model_size,
        language,
        _sync_progress_bridge if progress_callback else None,
    )

    async with aiofiles.open(output_transcript_path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(result, indent=2, ensure_ascii=False))

    return result
