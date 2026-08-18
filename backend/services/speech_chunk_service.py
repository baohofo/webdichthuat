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
SENTENCE_TERMINATORS = re.compile(r"(?<!\.)[.!?]+$")
ELLIPSIS_TERMINATORS = re.compile(r"(\.{3,}|…)+$")
CLAUSE_TERMINATORS = re.compile(r"[,;:]+$")
LEADING_CONTINUATION = re.compile(r"^(\.{2,}|…|\s|,)+")


def is_sentence_ending(text: str) -> bool:
    """Kiểm tra văn bản có kết thúc bằng dấu chấm, hỏi, than (không tính ellipsis thuần túy) không."""
    clean = text.strip()
    return bool(SENTENCE_TERMINATORS.search(clean))


def is_ellipsis_ending(text: str) -> bool:
    """Kiểm tra văn bản có kết thúc bằng dấu ba chấm lửng (...) hay (…)."""
    clean = text.strip()
    return bool(ELLIPSIS_TERMINATORS.search(clean))


def is_clause_ending(text: str) -> bool:
    """Kiểm tra văn bản có kết thúc bằng dấu phẩy, chấm phẩy, hai chấm không."""
    clean = text.strip()
    return bool(CLAUSE_TERMINATORS.search(clean))


def is_continuation_fragment(prev_text: str, next_text: str) -> bool:
    """
    Nhận diện fragment tiếp theo có phải là phần nối tiếp trực tiếp của câu trước hay không:
    - Câu trước kết thúc bằng '...' hoặc '…' và câu sau bắt đầu bằng '...' hoặc chữ thường.
    - Hoặc câu trước chưa kết thúc dấu câu và câu sau là từ nối.
    """
    clean_prev = prev_text.strip()
    clean_next = next_text.strip()
    if not clean_prev or not clean_next:
        return False

    prev_has_ellipsis = is_ellipsis_ending(clean_prev)
    next_has_leading_ellipsis = bool(LEADING_CONTINUATION.search(clean_next))

    # Nếu A có '...' và B có leading '...' -> chắc chắn là continuation
    if prev_has_ellipsis and next_has_leading_ellipsis:
        return True

    # Nếu A có '...' và B bắt đầu bằng chữ thường
    first_char = clean_next[0]
    if prev_has_ellipsis and (first_char.islower() or first_char in {",", ";"}):
        return True

    # Nếu A không có dấu ngắt câu nào và B bắt đầu bằng chữ thường
    if not is_sentence_ending(clean_prev) and not is_clause_ending(clean_prev) and not prev_has_ellipsis:
        if first_char.islower():
            return True

    return False


def get_trailing_punctuation(text: str) -> str:
    """Trích xuất ký tự dấu câu ở cuối chuỗi."""
    clean = text.strip()
    if not clean:
        return ""
    if is_ellipsis_ending(clean):
        return "…"
    last_char = clean[-1]
    if last_char in {".", "!", "?"}:
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


def merge_continuation_speech_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Gộp các SpeechChunks liền kề nếu chúng là 2 vế của một câu liên tục bị tách vụn
    bởi dấu ba chấm lửng (...) hoặc continuation marker, khi gap nhỏ và tổng thời lượng <= 9.0s.
    """
    if not chunks:
        return []

    merged: List[Dict[str, Any]] = []

    for chunk in chunks:
        if not merged:
            merged.append(chunk)
            continue

        prev = merged[-1]
        prev_end = float(prev.get("end", 0.0))
        curr_start = float(chunk.get("start", prev_end))
        gap = max(0.0, curr_start - prev_end)
        combined_dur = float(chunk.get("end", curr_start + 1.0)) - float(prev.get("start", 0.0))

        prev_text = prev.get("original_text", "").strip()
        curr_text = chunk.get("original_text", "").strip()

        # Kiểm tra điều kiện continuation
        if is_continuation_fragment(prev_text, curr_text) and gap <= CHUNK_MERGE_MAX_GAP and combined_dur <= HARD_MAX_CHUNK_DURATION:
            # Gộp vào chunk trước
            clean_prev = re.sub(r"(\.{2,}|…|\s)+$", "", prev_text)
            clean_curr = re.sub(r"^(\.{2,}|…|\s)+", "", curr_text)
            joined_text = f"{clean_prev} {clean_curr}".strip()

            prev["end"] = chunk.get("end", curr_start + 1.0)
            prev["duration"] = round(float(prev["end"]) - float(prev["start"]), 2)
            prev["original_text"] = joined_text
            prev["punctuation_end"] = get_trailing_punctuation(joined_text)
            prev["is_complete_sentence"] = is_sentence_ending(joined_text)
            prev["original_whisper_indices"] = list(set(prev.get("original_whisper_indices", []) + chunk.get("original_whisper_indices", [])))
            prev["words"] = prev.get("words", []) + chunk.get("words", [])
            continue

        merged.append(chunk)

    # Re-index
    for idx, c in enumerate(merged, start=1):
        c["index"] = idx

    return merged


def build_speech_chunks_from_stt(
    whisper_segments: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Gom nhóm (Semantic Chunking) các Whisper segments thành các SpeechChunk hoàn chỉnh cho TTS:
    - Ưu tiên thứ tự: Sentence boundary -> Semantic relation -> Original gap -> Max duration
    - Nhận diện continuation marker: không cắt vụn câu khi có '...' nối vế.
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
        is_continuation = is_continuation_fragment(prev_text, seg_text)

        # Kiểm tra điều kiện ngắt chunk
        should_split = False

        # 1. Nếu đạt Hard Max (>= 9.0s) -> Bắt buộc ngắt
        if potential_duration >= HARD_MAX_CHUNK_DURATION:
            should_split = True
        # 2. Nếu là continuation và chưa vượt hard max -> Giữ lại không split
        elif is_continuation and potential_duration < HARD_MAX_CHUNK_DURATION:
            should_split = False
        # 3. Nếu đạt Soft Max (>= 7.0s) và segment trước có dấu ngắt ý (chấm hoặc phẩy)
        elif potential_duration >= SOFT_MAX_CHUNK_DURATION and (prev_is_sentence_end or prev_is_clause_end or gap > 0.3):
            should_split = True
        # 4. Nếu segment trước kết thúc câu hoàn chỉnh (. ! ?)
        elif prev_is_sentence_end:
            current_dur = prev_end - chunk_start
            # Nếu câu trước đã đạt thời lượng tối thiểu hoặc có khoảng nghỉ rõ ràng
            if current_dur >= PREFERRED_CHUNK_MIN_DURATION or gap > CHUNK_MERGE_MAX_GAP:
                should_split = True
            # Nếu là câu ngắn nhưng độc lập (ví dụ "Yes.", "No.", "Right.") và có khoảng cách
            elif gap >= 0.35:
                should_split = True
        # 5. Nếu khoảng nghỉ gốc quá lớn (> 0.8s) -> Thường là chuyển cảnh/ngừng lời
        elif gap > 0.8:
            should_split = True

        if should_split:
            _flush_current_chunk()
            current_segments.append(seg)
        else:
            current_segments.append(seg)

    # Đóng chunk cuối cùng nếu còn
    _flush_current_chunk()

    # Chạy qua bộ gộp continuation chunks sau cùng để làm sạch triệt để
    final_chunks = merge_continuation_speech_chunks(chunks)

    logger.info(
        f"✓ Semantic Chunking hoàn tất: {len(whisper_segments)} Whisper segments -> {len(final_chunks)} SpeechChunks "
        f"(Avg chunk duration: {round(sum(c['duration'] for c in final_chunks) / max(1, len(final_chunks)), 2)}s)"
    )

    return final_chunks
