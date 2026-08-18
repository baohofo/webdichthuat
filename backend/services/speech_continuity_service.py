import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.config import (
    CONTINUITY_GAP_THRESHOLD_SEC,
    CONTINUITY_MAX_PHRASE_CHARS,
    CONTINUITY_MAX_PHRASE_DURATION,
    CONTINUITY_MIN_NATURAL_PAUSE_SEC,
)
from backend.services.tts_service import normalize_spoken_text_for_tts

logger = logging.getLogger("speech_continuity_service")

# Danh sách từ nối / liên từ / đại từ nối thường xuất hiện ở mệnh đề tiếp diễn tiếng Việt
CONTINUATION_LEAD_PATTERNS = [
    r"^(và|nhưng|mà|để|là|khi|thì|rồi|nên|với|trong|của|ở|chứ|bởi|vì|do|nếu|tuy|mặc dù|cho dù|hay|hoặc)\b",
    r"^(thì phải|và phá|đủ sức|không thì|lại còn|đang có|cũng có|sẽ là|mới là|nhất định|được rồi)\b",
    r"^(nó|hắn|chúng nó|chúng ta|mình|tao|cậu|anh|chị|em|bọn chúng|gã đó|tiểu nhan)\b",
]

TERMINAL_PUNCTUATION = {".", "!", "?", "…", "..."}


def is_strong_sentence_terminal(text: str, punct_hint: Optional[str] = None) -> bool:
    """
    Kiểm tra xem câu/mệnh đề có kết thúc bằng dấu chấm dứt khoát hay không (. ! ?).
    Dấu phẩy (,), gạch ngang (-), hoặc không có dấu được xem là mệnh đề mở.
    """
    clean = text.strip()
    if not clean:
        return False
    if clean.endswith("...") or clean.endswith("…"):
        return True
    last_char = clean[-1]
    if last_char in {".", "!", "?"}:
        return True
    if punct_hint and punct_hint in {".", "!", "?", "…", "..."}:
        return True
    return False


def is_continuation_clause(next_text: str, prev_text: str = "") -> Tuple[bool, str]:
    """
    Đánh giá nhiều tín hiệu ngôn ngữ học để xác định xem next_text có phải là
    mệnh đề tiếp nối trực tiếp của prev_text hay không.
    """
    t = next_text.strip()
    if not t:
        return False, "empty_text"

    # Tín hiệu 1: Bắt đầu bằng chữ thường
    first_char = t[0]
    if first_char.islower():
        return True, "starts_with_lowercase"

    # Tín hiệu 2: Bắt đầu bằng dấu 3 chấm nối
    if t.startswith("...") or t.startswith("…"):
        return True, "starts_with_ellipsis_continuation"

    # Tín hiệu 3: Bắt đầu bằng từ nối / liên từ
    t_lower = t.lower()
    for pat in CONTINUATION_LEAD_PATTERNS:
        if re.search(pat, t_lower):
            return True, f"matched_continuation_pattern({pat})"

    # Tín hiệu 4: prev_text kết thúc bằng từ mở (ví dụ: "có", "là", "để", "thì", "được")
    p_lower = prev_text.strip().lower()
    if p_lower:
        last_words = p_lower.split()[-2:]
        last_phrase = " ".join(last_words)
        if any(last_phrase.endswith(w) for w in ["là", "có", "để", "thì", "với", "của", "trong", "rằng", "đang"]):
            return True, f"prev_ends_with_open_connector({last_phrase})"

    return False, "not_continuation"


def analyze_speech_continuity(
    speech_chunks: List[Dict[str, Any]],
    style: str = "movie_review_spoken_vi",
    gap_threshold: float = CONTINUITY_GAP_THRESHOLD_SEC,
    max_phrase_dur: float = CONTINUITY_MAX_PHRASE_DURATION,
    max_phrase_chars: int = CONTINUITY_MAX_PHRASE_CHARS,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Speech Continuity Analyzer:
    Tách biệt Subtitle Segmentation (phụ đề từng dòng) khỏi TTS Speech Segmentation (cụm lời nói liên tục).
    
    Quy tắc phân tích đa tín hiệu:
    - Nếu source_gap <= gap_threshold
    - VÀ câu A không kết thúc bằng dấu ngắt mạnh (. ! ?)
    - VÀ câu B có dấu hiệu là mệnh đề tiếp diễn (lowercase, liên từ, hoặc câu A chưa trọn ý)
    - VÀ tổng thời lượng phrase sau khi gộp <= max_phrase_dur (8.0s)
    - VÀ tổng số ký tự <= max_phrase_chars (160 chars)
    => Ghép thành 1 TTS Phrase duy nhất để Edge-TTS đọc liền mạch, triệt tiêu tiếng thở vụn/micro-gap.
    
    Bảo toàn 100% các khoảng nghỉ tự nhiên khi source_gap lớn (> gap_threshold) hoặc câu trước đã kết thúc trọn ý.
    """
    if not speech_chunks:
        return [], []

    tts_phrases: List[Dict[str, Any]] = []
    debug_entries: List[Dict[str, Any]] = []

    # Nhóm phrase hiện tại
    current_members: List[Dict[str, Any]] = [speech_chunks[0]]

    for i in range(len(speech_chunks) - 1):
        chunk_a = speech_chunks[i]
        chunk_b = speech_chunks[i + 1]

        start_a = float(chunk_a.get("start", 0.0))
        end_a = float(chunk_a.get("end", start_a + 1.0))
        start_b = float(chunk_b.get("start", end_a))
        end_b = float(chunk_b.get("end", start_b + 1.0))

        source_gap = round(max(0.0, start_b - end_a), 3)

        text_a = (chunk_a.get("translated_text") or chunk_a.get("original_text") or "").strip()
        text_b = (chunk_b.get("translated_text") or chunk_b.get("original_text") or "").strip()
        punct_a = chunk_a.get("punctuation_end", "")

        is_terminal_a = is_strong_sentence_terminal(text_a, punct_a)
        is_cont_b, cont_reason = is_continuation_clause(text_b, text_a)

        # Tính toán tiềm năng gộp
        phrase_start = float(current_members[0].get("start", 0.0))
        projected_dur = round(end_b - phrase_start, 2)
        projected_text_len = sum(len((m.get("translated_text") or m.get("original_text") or "").strip()) for m in current_members) + len(text_b)

        should_merge = False
        decision_reason = ""

        if projected_dur > max_phrase_dur:
            should_merge = False
            decision_reason = f"rejected_duration_limit({projected_dur:.2f}s > {max_phrase_dur:.1f}s)"
        elif projected_text_len > max_phrase_chars:
            should_merge = False
            decision_reason = f"rejected_text_length_limit({projected_text_len} > {max_phrase_chars})"
        elif source_gap > gap_threshold:
            should_merge = False
            decision_reason = f"rejected_source_gap({source_gap:.2f}s > {gap_threshold:.2f}s, natural pause preserved)"
        elif is_terminal_a and not is_cont_b:
            should_merge = False
            decision_reason = f"rejected_sentence_completed_with_terminal_punct('{text_a[-1]}')"
        elif source_gap <= 0.05 and not is_terminal_a:
            should_merge = True
            decision_reason = f"merged_zero_source_gap({source_gap:.2f}s <= 0.05s, open clause)"
        elif not is_terminal_a and is_cont_b:
            should_merge = True
            decision_reason = f"merged_clause_continuation({cont_reason}, gap={source_gap:.2f}s)"
        elif not is_terminal_a and source_gap <= gap_threshold:
            should_merge = True
            decision_reason = f"merged_open_clause({source_gap:.2f}s <= {gap_threshold:.2f}s)"
        elif is_cont_b and source_gap <= 0.20:
            should_merge = True
            decision_reason = f"merged_tight_gap_continuation({cont_reason}, gap={source_gap:.2f}s)"
        else:
            should_merge = False
            decision_reason = f"rejected_default_boundary(gap={source_gap:.2f}s)"

        debug_entries.append({
            "chunk_a_index": chunk_a.get("index", i + 1),
            "chunk_b_index": chunk_b.get("index", i + 2),
            "text_a": text_a,
            "text_b": text_b,
            "source_gap_sec": source_gap,
            "is_terminal_a": is_terminal_a,
            "is_continuation_b": is_cont_b,
            "merged_for_tts": should_merge,
            "reason": decision_reason,
        })

        if should_merge:
            current_members.append(chunk_b)
        else:
            # Hoàn tất phrase hiện tại và bắt đầu phrase mới
            phrase = _build_phrase_from_members(len(tts_phrases) + 1, current_members, style)
            tts_phrases.append(phrase)
            current_members = [chunk_b]

    # Đóng phrase cuối cùng
    if current_members:
        phrase = _build_phrase_from_members(len(tts_phrases) + 1, current_members, style)
        tts_phrases.append(phrase)

    logger.info(
        f"[SPEECH_CONTINUITY] Input: {len(speech_chunks)} speech chunks -> "
        f"Output: {len(tts_phrases)} continuous TTS phrases (Merged: {len(speech_chunks) - len(tts_phrases)} boundaries)"
    )

    return tts_phrases, debug_entries


def _build_phrase_from_members(
    phrase_id: int,
    members: List[Dict[str, Any]],
    style: str,
) -> Dict[str, Any]:
    """
    Xây dựng một TTSPhrase chuẩn xác từ danh sách các SpeechChunk thành viên.
    """
    first = members[0]
    last = members[-1]

    phrase_start = float(first.get("start", 0.0))
    phrase_end = float(last.get("end", phrase_start + 1.0))
    phrase_dur = round(phrase_end - phrase_start, 2)

    # Nối văn bản dịch hiển thị
    display_texts = [(m.get("translated_text") or m.get("original_text") or "").strip() for m in members]
    display_text_full = " ".join(t for t in display_texts if t)

    # Chuẩn hóa văn bản đọc chuyên biệt cho TTS
    spoken_text = normalize_spoken_text_for_tts(display_text_full, style=style)

    member_indices = [int(m.get("index", 0)) for m in members]
    whisper_indices = []
    for m in members:
        whisper_indices.extend(m.get("original_whisper_indices", []))

    return {
        "index": phrase_id,
        "phrase_id": phrase_id,
        "start": phrase_start,
        "end": phrase_end,
        "duration": phrase_dur,
        "text": display_text_full,
        "display_text": display_text_full,
        "spoken_text": spoken_text,
        "translated_text": display_text_full,
        "source_chunks": member_indices,
        "punctuation_end": last.get("punctuation_end", ""),
        "is_complete_sentence": last.get("is_complete_sentence", False),
        "original_text": " ".join((m.get("original_text") or "").strip() for m in members),
        "original_whisper_indices": sorted(list(set(whisper_indices))),
        "member_count": len(members),
    }
