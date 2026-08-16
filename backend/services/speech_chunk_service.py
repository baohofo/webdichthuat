import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.config import (
    CHUNK_MERGE_MAX_GAP,
    HARD_MAX_CHUNK_DURATION,
    PREFERRED_CHUNK_MAX_DURATION,
    PREFERRED_CHUNK_MIN_DURATION,
    SOFT_MAX_CHUNK_DURATION,
)

logger = logging.getLogger("speech_chunk_service")

# Regex nhận diện kết thúc câu
SENTENCE_TERMINATORS = re.compile(r"[.!?…]+$")
CLAUSE_TERMINATORS = re.compile(r"[,;:]+$")


def is_sentence_ending(text: str) -> bool:
    """Kiểm tra văn bản có kết thúc bằng dấu chấm, hỏi, than không."""
    clean = text.strip()
    return bool(SENTENCE_TERMINATORS.search(clean))


def is_clause_ending(text: str) -> bool:
    """Kiểm tra văn bản có kết thúc bằng dấu phẩy, chấm phẩy, hai chấm không."""
    clean = text.strip()
    return bool(CLAUSE_TERMINATORS.search(clean))


def get_trailing_punctuation(text: str) -> str:
    """Trích xuất ký tự dấu câu ở cuối chuỗi."""
    clean = text.strip()
    if not clean:
        return ""
    last_char = clean[-1]
    if last_char in {".", "!", "?", "…"}:
        return last_char
    if last_char in {",", ";", ":"}:
        return last_char
    return ""


def _split_oversized_segment(seg: Dict[str, Any], target_max_dur: float = SOFT_MAX_CHUNK_DURATION) -> List[Dict[str, Any]]:
    """
    Tự động chia nhỏ một Whisper segment đơn lẻ nếu nó quá dài (> 7-9s):
    - Tách theo dấu phẩy, chấm phẩy hoặc ranh giới mệnh đề tự nhiên.
    - Phân bổ timestamp tương ứng theo word timestamps hoặc tỷ lệ ký tự.
    """
    text = seg.get("original_text", "").strip()
    seg_start = float(seg.get("start", 0.0))
    seg_end = float(seg.get("end", seg_start + 1.0))
    seg_dur = max(0.5, seg_end - seg_start)

    if seg_dur <= HARD_MAX_CHUNK_DURATION:
        return [seg]

    # Thử tách theo dấu phẩy hoặc chấm phẩy
    clauses = re.split(r"(?<=[,;:])\s+", text)
    if len(clauses) <= 1:
        # Thử tách theo khoảng trắng giữa câu
        words = text.split(" ")
        if len(words) >= 10:
            mid = len(words) // 2
            clauses = [" ".join(words[:mid]), " ".join(words[mid:])]
        else:
            return [seg]

    sub_segs = []
    total_chars = sum(len(c) for c in clauses)
    curr_start = seg_start

    for idx, clause in enumerate(clauses):
        clean_c = clause.strip()
        if not clean_c:
            continue
        c_ratio = len(clean_c) / max(1, total_chars)
        c_dur = seg_dur * c_ratio
        c_end = seg_end if idx == len(clauses) - 1 else round(curr_start + c_dur, 2)
        c_end = round(min(seg_end, max(curr_start + 0.3, c_end)), 2)

        sub_segs.append({
            "index": seg.get("index", 1),
            "start": round(curr_start, 2),
            "end": c_end,
            "duration": round(c_end - curr_start, 2),
            "original_text": clean_c,
            "words": [],
        })
        curr_start = c_end

    return sub_segs


def build_speech_chunks_from_stt(
    whisper_segments: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Gom nhóm (Semantic Chunking) các Whisper segments thành các SpeechChunk hoàn chỉnh cho TTS:
    - Ưu tiên thứ tự: Sentence boundary -> Semantic relation -> Original gap -> Max duration
    - Không cắt vụn câu chỉ vì Whisper sinh nhiều segment nhỏ.
    - Câu ngắn độc lập hoàn chỉnh ('Đúng vậy.', 'Không.') vẫn được bảo lưu.
    - Điểm cắt ưu tiên trong khoảng 2.0 - 6.0s, soft max 7.0s, hard max 9.0s.
    """
    if not whisper_segments:
        return []

    # 1. Tiền xử lý: Tách các segment đơn lẻ quá khổ (> 9s)
    expanded_segments: List[Dict[str, Any]] = []
    for s in whisper_segments:
        expanded_segments.extend(_split_oversized_segment(s))

    chunks: List[Dict[str, Any]] = []
    current_segments: List[Dict[str, Any]] = []

    def _flush_current_chunk():
        if not current_segments:
            return

        first_seg = current_segments[0]
        last_seg = current_segments[-1]

        start_time = float(first_seg.get("start", 0.0))
        end_time = float(last_seg.get("end", start_time + 1.0))
        total_duration = round(max(0.2, end_time - start_time), 2)

        # Ghép text liền mạch
        merged_texts = [s.get("original_text", "").strip() for s in current_segments if s.get("original_text")]
        merged_text = " ".join(merged_texts).strip()

        # Ghép word timestamps
        all_words: List[Dict[str, Any]] = []
        for s in current_segments:
            all_words.extend(s.get("words", []))

        orig_indices = [int(s.get("index", 0)) for s in current_segments if "index" in s]

        punct = get_trailing_punctuation(merged_text)
        is_complete = is_sentence_ending(merged_text)

        chunks.append({
            "index": len(chunks) + 1,
            "start": round(start_time, 2),
            "end": round(end_time, 2),
            "duration": total_duration,
            "original_text": merged_text,
            "translated_text": "",
            "punctuation_end": punct,
            "is_complete_sentence": is_complete,
            "original_whisper_indices": orig_indices,
            "words": all_words,
        })
        current_segments.clear()

    for idx, seg in enumerate(expanded_segments):
        seg_text = seg.get("original_text", "").strip()
        if not seg_text:
            continue

        if not current_segments:
            current_segments.append(seg)
            continue

        prev_seg = current_segments[-1]
        prev_end = float(prev_seg.get("end", 0.0))
        seg_start = float(seg.get("start", prev_end))
        gap = max(0.0, seg_start - prev_end)

        chunk_start = float(current_segments[0].get("start", 0.0))
        seg_end = float(seg.get("end", seg_start + 1.0))
        potential_duration = seg_end - chunk_start

        prev_text = prev_seg.get("original_text", "").strip()
        prev_is_sentence_end = is_sentence_ending(prev_text)
        prev_is_clause_end = is_clause_ending(prev_text)

        # Kiểm tra điều kiện ngắt chunk
        should_split = False

        # 1. Nếu đạt Hard Max (>= 9.0s) -> Bắt buộc ngắt
        if potential_duration >= HARD_MAX_CHUNK_DURATION:
            should_split = True
        # 2. Nếu đạt Soft Max (>= 7.0s) và segment trước có dấu ngắt ý (chấm hoặc phẩy)
        elif potential_duration >= SOFT_MAX_CHUNK_DURATION and (prev_is_sentence_end or prev_is_clause_end or gap > 0.3):
            should_split = True
        # 3. Nếu segment trước kết thúc câu hoàn chỉnh (. ! ?)
        elif prev_is_sentence_end:
            current_dur = prev_end - chunk_start
            # Nếu câu trước đã đạt thời lượng tối thiểu hoặc có khoảng nghỉ rõ ràng
            if current_dur >= PREFERRED_CHUNK_MIN_DURATION or gap > CHUNK_MERGE_MAX_GAP:
                should_split = True
            # Nếu là câu ngắn nhưng độc lập (ví dụ "Yes.", "No.", "Right.") và có khoảng cách
            elif gap >= 0.35:
                should_split = True
        # 4. Nếu khoảng nghỉ gốc quá lớn (> 0.8s) -> Thường là chuyển cảnh/ngừng lời
        elif gap > 0.8:
            should_split = True

        if should_split:
            _flush_current_chunk()
            current_segments.append(seg)
        else:
            current_segments.append(seg)

    # Đóng chunk cuối cùng nếu còn
    _flush_current_chunk()

    logger.info(
        f"✓ Semantic Chunking hoàn tất: {len(whisper_segments)} Whisper segments -> {len(chunks)} SpeechChunks "
        f"(Avg chunk duration: {round(sum(c['duration'] for c in chunks) / max(1, len(chunks)), 2)}s)"
    )

    return chunks
