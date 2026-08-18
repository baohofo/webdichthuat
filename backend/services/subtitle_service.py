import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import aiofiles

from backend.config import (
    SUBTITLE_GAP_WARNING_THRESHOLD,
    SUBTITLE_MAX_CHARS_PER_LINE,
    SUBTITLE_MAX_CPS,
    SUBTITLE_MAX_LINES,
    SUBTITLE_TARGET_CPS,
    SUBTITLE_WARN_OVER_DURATION,
    SUBTITLE_WARN_UNDER_DURATION,
)

logger = logging.getLogger("subtitle_service")


def format_timestamp_srt(seconds: float) -> str:
    """
    Chuyển đổi số giây thành định dạng timestamp SRT chuẩn: HH:MM:SS,mmm
    Ví dụ: 75.45 -> 00:01:15,450
    """
    total_ms = max(0, int(round(seconds * 1000)))
    hours = total_ms // 3600000
    remainder = total_ms % 3600000
    minutes = remainder // 60000
    remainder %= 60000
    secs = remainder // 1000
    ms = remainder % 1000

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def calculate_cps(text: str, duration: float) -> float:
    """
    Tính tốc độ đọc ký tự trên giây (Characters Per Second - CPS).
    Loại bỏ dấu xuống dòng để tính toán chính xác số ký tự hiển thị.
    """
    clean_text = re.sub(r"\s+", " ", text).strip()
    char_count = len(clean_text)
    safe_dur = max(0.1, duration)
    return round(char_count / safe_dur, 2)


def wrap_text_lines(
    text: str,
    max_chars_per_line: int = SUBTITLE_MAX_CHARS_PER_LINE,
    max_lines: int = SUBTITLE_MAX_LINES,
) -> str:
    """
    Ngắt dòng văn bản phụ đề một cách tự nhiên theo ranh giới từ.
    Tuyệt đối KHÔNG cắt giữa từ (như 'hiệu' / 'ứng').
    """
    clean_text = re.sub(r"\s+", " ", text).strip()
    if not clean_text:
        return ""

    if len(clean_text) <= max_chars_per_line:
        return clean_text

    words = clean_text.split(" ")
    lines: List[str] = []
    current_line: List[str] = []
    current_length = 0

    for word in words:
        word_len = len(word)
        if current_line and (current_length + 1 + word_len > max_chars_per_line):
            lines.append(" ".join(current_line))
            current_line = [word]
            current_length = word_len
        else:
            current_line.append(word)
            current_length += (1 if current_length > 0 else 0) + word_len

    if current_line:
        lines.append(" ".join(current_line))

    # Nếu vượt quá số dòng tối đa cho phép, kết hợp các dòng cuối
    if len(lines) > max_lines:
        lines = lines[: max_lines - 1] + [" ".join(lines[max_lines - 1 :])]

    return "\n".join(lines)


def _find_split_points(text: str) -> List[str]:
    """
    Tìm các điểm phân đoạn tự nhiên theo dấu câu hoặc cụm từ ngữ nghĩa.
    """
    # 1. Thử tách theo dấu kết thúc câu (. ? !)
    sentences = re.split(r"(?<=[.?!])\s+", text)
    if len(sentences) > 1 and all(s.strip() for s in sentences):
        return [s.strip() for s in sentences if s.strip()]

    # 2. Thử tách theo dấu phẩy, chấm phẩy, hai chấm (, ; :)
    clauses = re.split(r"(?<=[,;:])\s+", text)
    if len(clauses) > 1 and all(c.strip() for c in clauses):
        return [c.strip() for c in clauses if c.strip()]

    # 3. Tách theo cụm từ ở khoảng giữa văn bản (dựa vào khoảng trắng)
    words = text.split(" ")
    if len(words) >= 8:
        mid = len(words) // 2
        part1 = " ".join(words[:mid])
        part2 = " ".join(words[mid:])
        return [part1, part2]

    return [text]


def merge_short_subtitles(raw_subtitles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Short Fragment Merger:
    - Loại bỏ các mảnh phụ đề vụn (< 1.0s hoặc 1-2 từ không hoàn chỉnh).
    - Bảo lưu các câu ngắn hoàn chỉnh (1-3 từ kết thúc câu như 'Không.', 'Đúng vậy.').
    - Gộp các mảnh dở dang vào phụ đề liền kề nếu khoảng cách < 0.6s và tổng thời lượng <= 5.5s.
    """
    if not raw_subtitles:
        return []

    merged: List[Dict[str, Any]] = []
    
    for sub in raw_subtitles:
        text = sub.get("text", "").strip()
        if not text:
            continue

        words = text.split(" ")
        word_count = len(words)
        dur = float(sub.get("duration", 0.0))
        is_sentence_end = bool(re.search(r"[.!?…]$", text))

        # Kiểm tra xem có phải câu ngắn độc lập hoàn chỉnh không
        if dur < 1.0 and word_count <= 3 and is_sentence_end and sub.get("cps", 0.0) <= 22:
            merged.append(sub)
            continue

        # Nếu là fragment ngắn (< 1.2s hoặc < 4 từ) và có thể gộp với sub trước đó
        if merged and (dur < 1.1 or word_count <= 3):
            prev = merged[-1]
            prev_end = float(prev["end"])
            curr_start = float(sub["start"])
            gap = max(0.0, curr_start - prev_end)
            combined_dur = float(sub["end"]) - float(prev["start"])

            # Nếu khoảng nghỉ nhỏ và tổng thời lượng không quá 5.5s
            if gap <= 0.6 and combined_dur <= 5.5:
                # Gộp vào sub trước
                combined_text = f"{prev['text']} {text}".strip()
                prev["end"] = sub["end"]
                prev["duration"] = round(combined_dur, 2)
                prev["text"] = wrap_text_lines(combined_text)
                prev["cps"] = calculate_cps(combined_text, combined_dur)
                continue

        merged.append(sub)

    # Re-index
    for idx, s in enumerate(merged, start=1):
        s["id"] = idx

    return merged


def balance_subtitle_cps(subtitles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    CPS Balancer:
    - Nếu một phụ đề có CPS quá cao (> 20.0), kiểm tra khoảng trống (gap) tới phụ đề kế tiếp
    - Mở rộng thời gian hiển thị vào khoảng trống an toàn để hạ CPS xuống mức đọc tự nhiên (17-20).
    """
    for idx, sub in enumerate(subtitles):
        text = sub.get("text", "").strip()
        dur = float(sub.get("duration", 0.0))
        cps = calculate_cps(text, dur)

        if cps > 20.0 and idx + 1 < len(subtitles):
            next_start = float(subtitles[idx + 1]["start"])
            curr_end = float(sub["end"])
            gap = next_start - curr_end

            if gap > 0.15:
                # Mở rộng thêm tối đa gap - 0.05s
                expand = min(gap - 0.05, (len(text) / SUBTITLE_TARGET_CPS) - dur)
                if expand > 0.05:
                    new_end = round(curr_end + expand, 2)
                    new_dur = round(new_end - float(sub["start"]), 2)
                    sub["end"] = new_end
                    sub["duration"] = new_dur
                    sub["cps"] = calculate_cps(text, new_dur)

    return subtitles


def segment_speech_into_subtitles(speech_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Chuyển đổi danh sách SpeechSegment/SpeechChunk sang SubtitleSegment độc lập:
    - Áp dụng phân đoạn ngữ nghĩa tự nhiên
    - Chạy qua Short Fragment Merger & CPS Balancer
    """
    subtitles: List[Dict[str, Any]] = []
    sub_index = 1

    for seg in speech_segments:
        speech_id = seg.get("index", sub_index)
        text = (seg.get("translated_text") or seg.get("original_text") or "").strip()
        if not text:
            continue

        seg_start = float(seg.get("start", 0.0))
        seg_end = float(seg.get("end", seg_start + 1.0))
        seg_duration = max(0.4, seg_end - seg_start)
        cps = calculate_cps(text, seg_duration)
        char_count = len(text)

        # Kiểm tra xem có cần phân đoạn phụ đề nhỏ hơn không (> 5.5s hoặc > 2 lines)
        needs_split = (
            seg_duration > 5.5
            or cps > SUBTITLE_MAX_CPS
            or char_count > (SUBTITLE_MAX_CHARS_PER_LINE * 2)
        )

        if needs_split:
            parts = _find_split_points(text)
            if len(parts) > 1:
                total_chars = sum(len(p) for p in parts)
                current_sub_start = seg_start

                for p_idx, part in enumerate(parts):
                    part_ratio = len(part) / max(1, total_chars)
                    part_dur = seg_duration * part_ratio

                    if p_idx == len(parts) - 1:
                        part_end = seg_end
                    else:
                        part_end = round(current_sub_start + part_dur, 2)

                    part_end = round(min(seg_end, part_end), 2)
                    wrapped_part = wrap_text_lines(part)
                    actual_part_dur = max(0.2, part_end - current_sub_start)

                    subtitles.append({
                        "id": sub_index,
                        "speech_id": speech_id,
                        "start": round(current_sub_start, 2),
                        "end": part_end,
                        "duration": round(actual_part_dur, 2),
                        "text": wrapped_part,
                        "cps": calculate_cps(part, actual_part_dur),
                    })
                    sub_index += 1
                    current_sub_start = part_end
                continue

        # Không cần phân đoạn nhỏ hơn -> Format 1-2 dòng chuẩn
        wrapped_text = wrap_text_lines(text)
        subtitles.append({
            "id": sub_index,
            "speech_id": speech_id,
            "start": round(seg_start, 2),
            "end": round(seg_end, 2),
            "duration": round(seg_duration, 2),
            "text": wrapped_text,
            "cps": calculate_cps(text, seg_duration),
        })
        sub_index += 1

    # Chạy quy trình tối ưu phụ đề: Merger -> Balancer
    merged_subs = merge_short_subtitles(subtitles)
    balanced_subs = balance_subtitle_cps(merged_subs)

    return balanced_subs


def validate_and_sanitize_subtitles(
    subtitles: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Kiểm tra và chuẩn hóa danh sách phụ đề trước khi xuất file SRT:
    - Đảm bảo tính liên tục không overlap: subtitle[i].end <= subtitle[i+1].start
    - Đảm bảo start < end và không có thời gian âm
    - Phát hiện phụ đề quá dài (>6s) và khoảng trống lớn (>4s)
    - Xuất bảng tổng hợp metrics
    """
    sanitized: List[Dict[str, Any]] = []
    overlap_count = 0
    long_dur_count = 0
    high_cps_count = 0
    large_gap_count = 0
    under_08s_count = 0
    cps_list = []

    for i, sub in enumerate(subtitles):
        start = max(0.0, float(sub["start"]))
        end = float(sub["end"])
        if end <= start:
            end = start + 0.8

        # Kiểm tra overlap với phụ đề trước đó
        if sanitized:
            prev_end = sanitized[-1]["end"]
            if start < prev_end:
                overlap_count += 1
                logger.warning(
                    f"SUBTITLE_OVERLAP: Phụ đề #{sub['id']} ({start}s) overlap với #{sanitized[-1]['id']} ({prev_end}s). Tự động clamp."
                )
                start = round(prev_end + 0.01, 2)
                if end <= start:
                    end = round(start + 0.5, 2)

            # Kiểm tra khoảng trống lớn
            gap = start - prev_end
            if gap > SUBTITLE_GAP_WARNING_THRESHOLD:
                large_gap_count += 1
                logger.info(f"SUBTITLE_GAP: Khoảng trống {gap:.2f}s giữa #{sanitized[-1]['id']} và #{sub['id']}")

        duration = round(end - start, 2)
        text = sub["text"].strip()
        cps = calculate_cps(text, duration)
        cps_list.append(cps)

        if duration > SUBTITLE_WARN_OVER_DURATION:
            long_dur_count += 1

        if duration < SUBTITLE_WARN_UNDER_DURATION:
            under_08s_count += 1

        if cps > SUBTITLE_MAX_CPS:
            high_cps_count += 1

        sanitized.append({
            "id": i + 1,
            "speech_id": sub.get("speech_id", i + 1),
            "start": round(start, 2),
            "end": round(end, 2),
            "duration": duration,
            "text": text,
            "cps": cps,
        })

    max_cps = max(cps_list) if cps_list else 0.0
    avg_cps = round(sum(cps_list) / len(cps_list), 2) if cps_list else 0.0

    summary = {
        "subtitle_count": len(sanitized),
        "max_cps": max_cps,
        "average_cps": avg_cps,
        "overlap_count": overlap_count,
        "long_duration_count": long_dur_count,
        "under_08s_count": under_08s_count,
        "high_cps_count": high_cps_count,
        "large_gap_count": large_gap_count,
    }

    logger.info(
        f"✓ Subtitle validation hoàn tất: {len(sanitized)} subs, Avg CPS: {avg_cps}, Overlap: {overlap_count}"
    )

    return sanitized, summary


def format_timestamp_ass(seconds: float) -> str:
    """
    Chuyển đổi số giây thành định dạng timestamp ASS chuẩn: H:MM:SS.cc (ví dụ: 0:01:15.45)
    """
    total_cs = max(0, int(round(seconds * 100)))  # centiseconds
    hours = total_cs // 360000
    remainder = total_cs % 360000
    minutes = remainder // 6000
    remainder %= 6000
    secs = remainder // 100
    cs = remainder % 100

    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"


def hex_to_ass_color(hex_str: str, alpha: str = "00") -> str:
    """
    Chuyển đổi mã màu hex (#RRGGBB hoặc #RGB) sang định dạng màu ASS: &H<AA><BB><GG><RR>&
    """
    clean_hex = str(hex_str).strip().lstrip("#")
    if len(clean_hex) == 3:
        clean_hex = "".join([c * 2 for c in clean_hex])
    if len(clean_hex) != 6:
        clean_hex = "FFFFFF"  # fallback white

    r = clean_hex[0:2]
    g = clean_hex[2:4]
    b = clean_hex[4:6]

    return f"&H{alpha}{b}{g}{r}&"


def escape_ass_text(text: str) -> str:
    """
    Escape ký tự đặc biệt cho văn bản phụ đề ASS:
    - Chống lỗi syntax khi text chứa {, }, \
    - Chuyển đổi dấu xuống dòng thành \\N
    """
    if not text:
        return ""
    t = text.strip()
    # Thay thế dấu xuống dòng
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    lines = t.split("\n")
    escaped_lines = []
    for line in lines:
        l = line.strip()
        # Escape dấu ngoặc nhọn override tags
        l = l.replace("{", "\\{").replace("}", "\\}")
        escaped_lines.append(l)
    return "\\N".join(escaped_lines)


def generate_srt_content(subtitle_segments: List[Dict[str, Any]]) -> str:
    """
    Tạo nội dung file phụ đề SRT hoàn chỉnh từ danh sách SubtitleSegment đã validate.
    """
    srt_blocks = []
    for sub in subtitle_segments:
        idx = sub["id"]
        start_str = format_timestamp_srt(float(sub["start"]))
        end_str = format_timestamp_srt(float(sub["end"]))
        text = sub["text"].strip()
        if not text:
            continue

        block = f"{idx}\n{start_str} --> {end_str}\n{text}\n"
        srt_blocks.append(block)

    return "\n".join(srt_blocks)


def generate_ass_content(
    subtitle_segments: List[Dict[str, Any]],
    subtitle_style: Optional[Dict[str, Any]] = None,
    play_res_x: int = 1920,
    play_res_y: int = 1080,
) -> str:
    """
    Tạo nội dung file phụ đề ASS chuẩn xác từ cấu hình SubtitleStyle và danh sách phụ đề.
    Hỗ trợ định vị trực tiếp tọa độ tương đối (position_x, position_y, width, height) qua override tag {\\an5\\pos(X,Y)} và lề MarginL/MarginR.
    """
    style = subtitle_style or {}
    font_family = style.get("font_family") or "Arial"
    font_size = int(style.get("font_size") or 36)
    primary_color = hex_to_ass_color(style.get("primary_color") or "#FFFFFF")
    outline_color = hex_to_ass_color(style.get("outline_color") or "#000000")
    outline_width = float(style.get("outline_width") if style.get("outline_width") is not None else 2.5)
    shadow = float(style.get("shadow") if style.get("shadow") is not None else 1.0)
    bold = -1 if style.get("bold", True) else 0

    # Tọa độ và kích thước tương đối trực tiếp (0.0 đến 1.0) từ giao diện kéo thả & resize
    pos_x_ratio = float(style.get("position_x") if style.get("position_x") is not None else 0.50)
    pos_y_ratio = float(style.get("position_y") if style.get("position_y") is not None else 0.88)
    width_ratio = float(style.get("width") if style.get("width") is not None else 0.70)
    height_ratio = float(style.get("height") if style.get("height") is not None else 0.15)

    pos_x = int(round(pos_x_ratio * play_res_x))
    pos_y = int(round(pos_y_ratio * play_res_y))
    box_w = int(round(width_ratio * play_res_x))
    box_h = int(round(height_ratio * play_res_y))

    margin_l = max(10, pos_x - box_w // 2)
    margin_r = max(10, play_res_x - (pos_x + box_w // 2))
    margin_v = max(10, play_res_y - (pos_y + box_h // 2))

    pos_tag = f"{{\\an5\\pos({pos_x},{pos_y})}}"
    alignment = 5

    ass_header = f"""[Script Info]
Title: AI Dubbing Studio Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: {play_res_x}
PlayResY: {play_res_y}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_family},{font_size},{primary_color},&H000000FF&,{outline_color},&H80000000&,{bold},0,0,0,100,100,0,0,1,{outline_width},{shadow},{alignment},{margin_l},{margin_r},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    event_lines = []
    for sub in subtitle_segments:
        start_ass = format_timestamp_ass(float(sub["start"]))
        end_ass = format_timestamp_ass(float(sub["end"]))
        escaped_txt = escape_ass_text(sub.get("text", ""))
        if not escaped_txt:
            continue
        line = f"Dialogue: 0,{start_ass},{end_ass},Default,,0,0,0,,{pos_tag}{escaped_txt}"
        event_lines.append(line)

    return ass_header + "\n".join(event_lines) + "\n"


async def save_srt_file(
    speech_segments: List[Dict[str, Any]],
    output_srt_path: Path,
) -> Tuple[Path, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Quy trình: SpeechSegments -> SubtitleSegments -> Merger -> Balancer -> Validate -> Xuất file SRT.
    """
    output_srt_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Phân đoạn Speech thành Subtitles độc lập
    raw_subs = segment_speech_into_subtitles(speech_segments)

    # 2. Kiểm tra và validate chống overlap, CPS, độ dài
    valid_subs, summary = validate_and_sanitize_subtitles(raw_subs)

    # 3. Tạo nội dung SRT và lưu file UTF-8
    srt_content = generate_srt_content(valid_subs)
    async with aiofiles.open(output_srt_path, "w", encoding="utf-8") as f:
        await f.write(srt_content)

    logger.info(f"✓ Đã lưu file phụ đề SRT: {output_srt_path.name} ({len(valid_subs)} phụ đề)")
    return output_srt_path, valid_subs, summary


async def save_ass_file(
    valid_subtitles: List[Dict[str, Any]],
    output_ass_path: Path,
    subtitle_style: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    Xuất file phụ đề ASS với Subtitle Style tùy chỉnh phục vụ FFmpeg Burn-in.
    """
    output_ass_path.parent.mkdir(parents=True, exist_ok=True)
    ass_content = generate_ass_content(valid_subtitles, subtitle_style)
    async with aiofiles.open(output_ass_path, "w", encoding="utf-8") as f:
        await f.write(ass_content)

    logger.info(f"✓ Đã lưu file phụ đề ASS: {output_ass_path.name}")
    return output_ass_path


import json
from backend.utils.file_utils import get_job_paths
from backend.utils.job_store import load_job_info_sync, save_job_info_atomic_sync


async def ensure_subtitle_artifact(
    job_id: str,
    job_paths: Optional[Dict[str, Path]] = None,
    subtitle_type: str = "translated",
) -> Path:
    """
    Bảo đảm file phụ đề canonical (.srt) luôn tồn tại và hợp lệ:
    - subtitle_type = 'translated' -> sinh / kiểm tra translated.srt từ translated_transcript.json
    - subtitle_type = 'original'   -> sinh / kiểm tra original.srt từ transcript.json
    - TUYỆT ĐỐI KHÔNG GỌI LẠI GEMINI/WHISPER (Gemini API calls = 0).
    - Cập nhật atomic metadata artifacts vào job_info.json.
    """
    if not job_paths:
        job_paths = get_job_paths(job_id)
        if not job_paths:
            raise FileNotFoundError(f"Job '{job_id}' không tồn tại.")

    sub_type = "original" if str(subtitle_type).lower() in ["original", "goc", "source"] else "translated"
    filename_base = "original" if sub_type == "original" else "translated"
    srt_file = job_paths["subtitles_dir"] / f"{filename_base}.srt"
    ass_file = job_paths["subtitles_dir"] / f"{filename_base}.ass"

    if srt_file.exists() and srt_file.stat().st_size > 0:
        return srt_file

    trans_file = job_paths["transcript_dir"] / "translated_transcript.json"
    stt_file = job_paths["transcript_dir"] / "transcript.json"

    segments_to_use = []
    if sub_type == "translated":
        if trans_file.exists():
            try:
                async with aiofiles.open(trans_file, "r", encoding="utf-8") as f:
                    data = json.loads(await f.read())
                    segments_to_use = data.get("speech_chunks") or data.get("segments", [])
            except Exception as e:
                logger.warning(f"Lỗi đọc {trans_file.name}: {e}")

        if not segments_to_use and stt_file.exists():
            try:
                async with aiofiles.open(stt_file, "r", encoding="utf-8") as f:
                    data = json.loads(await f.read())
                    segments_to_use = data.get("speech_chunks") or data.get("segments", [])
            except Exception as e:
                logger.warning(f"Lỗi đọc {stt_file.name}: {e}")
    else:
        # Original subtitles
        if stt_file.exists():
            try:
                async with aiofiles.open(stt_file, "r", encoding="utf-8") as f:
                    data = json.loads(await f.read())
                    raw_chunks = data.get("speech_chunks") or data.get("segments", [])
                    # Đảm bảo dùng original_text
                    for c in raw_chunks:
                        segments_to_use.append({
                            **c,
                            "translated_text": c.get("original_text") or c.get("text", ""),
                        })
            except Exception as e:
                logger.warning(f"Lỗi đọc {stt_file.name}: {e}")

    if not segments_to_use:
        raise FileNotFoundError(
            f"Không tìm thấy dữ liệu phụ đề ({sub_type}) cho Job '{job_id}'."
        )

    # Sinh file SRT và ASS từ segments có sẵn (0 API calls)
    _, valid_subs, summary = await save_srt_file(segments_to_use, srt_file)
    try:
        await save_ass_file(valid_subs, ass_file)
    except Exception:
        pass

    # Cập nhật metadata artifact vào job_info.json
    try:
        job_info = load_job_info_sync(job_id)
        if job_info:
            artifacts = job_info.setdefault("artifacts", {})
            out_rev = job_info.get("output_revision", 1)
            art_key = f"{sub_type}_subtitle"
            artifacts[art_key] = {
                "available": True,
                "path": str(srt_file),
                "format": "srt",
                "count": len(valid_subs),
                "revision": out_rev,
            }
            if sub_type == "translated":
                job_info["subtitles_summary"] = summary
            save_job_info_atomic_sync(job_id, job_info)
    except Exception as e:
        logger.warning(f"Lỗi cập nhật artifact {sub_type}_subtitle vào job_info: {e}")

    logger.info(f"✓ Đã tự động tạo và bảo đảm canonical SRT artifact: {srt_file.name} ({len(valid_subs)} phụ đề)")
    return srt_file


async def ensure_translated_srt_artifact(
    job_id: str,
    job_paths: Optional[Dict[str, Path]] = None,
) -> Path:
    return await ensure_subtitle_artifact(job_id, job_paths, subtitle_type="translated")
