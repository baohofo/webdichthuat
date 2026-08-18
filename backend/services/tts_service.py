import asyncio
import hashlib
import json
import logging
import os
import re
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import edge_tts

from backend.config import (
    TTS_REQUEST_TIMEOUT,
    TTS_STUCK_THRESHOLD_SEC,
    TTS_CONCURRENCY,
    MIN_VALID_AUDIO_BYTES,
)

logger = logging.getLogger("tts_service")


def compute_tts_chunk_signature(
    voice: str,
    speed_rate: str,
    text: str,
    pitch: str = "+0Hz",
    translation_rev: int = 1,
    norm_version: str = "v2_pause_norm",
) -> str:
    """
    Tính signature SHA-256 xác thực cấu hình tạo giọng đọc cho từng SpeechChunk.
    Bao gồm toàn bộ các tham số ảnh hưởng trực tiếp đến waveform đầu ra:
    - voice: voice ID hoặc base_voice
    - speed_rate: tốc độ tổng hợp
    - pitch: cao độ giọng
    - text: normalized spoken text
    - translation_rev: phiên bản bản dịch
    - norm_version: phiên bản thuật toán normalization
    """
    payload = f"{voice.strip()}|{speed_rate.strip()}|{pitch.strip()}|{text.strip()}|rev_{translation_rev}|{norm_version}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_tts_checkpoint_atomic(checkpoint_file: Path, chunk_states: Dict[str, Any]) -> None:
    """
    Ghi file checkpoint tts_chunks_state.json theo cơ chế Atomic Write (.tmp + os.replace)
    kết hợp retry trên Windows để đảm bảo an toàn tuyệt đối ngay cả khi server bị crash.
    """
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file = checkpoint_file.parent / f"{checkpoint_file.stem}_{int(time.time()*1000)}.tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(chunk_states, f, indent=2, ensure_ascii=False)
        for attempt in range(5):
            try:
                os.replace(str(temp_file), str(checkpoint_file))
                break
            except (PermissionError, OSError):
                if attempt == 4:
                    with open(checkpoint_file, "w", encoding="utf-8") as f:
                        json.dump(chunk_states, f, indent=2, ensure_ascii=False)
                else:
                    time.sleep(0.01 * (attempt + 1))
    except Exception as e:
        logger.error(f"Lỗi atomic write tts_chunks_state: {e}", exc_info=True)
    finally:
        if temp_file.exists():
            try:
                temp_file.unlink(missing_ok=True)
            except Exception:
                pass

# Danh mục các phong cách giọng đọc AI phong phú theo ngôn ngữ
VOICE_CATALOG: Dict[str, List[Dict[str, Any]]] = {
    "vi": [
        # Nhóm: 🎬 Review Phim / TikTok
        {
            "id": "vi-VN-HoaiMyNeural_tiktok_review",
            "name": "Hoài My (Review Phim TikTok Kịch Tính)",
            "category": "🎬 Review Phim / TikTok",
            "gender": "Female",
            "base_voice": "vi-VN-HoaiMyNeural",
            "rate_offset": "+15%",
            "pitch": "+2Hz",
            "pause_profile": "movie_review",
            "recommended_translation_style": "movie_review_spoken_vi",
        },
        {
            "id": "vi-VN-HoaiMyNeural_tiktok_fast",
            "name": "Hoài My (Review Phim Nhịp Nhanh Cuốn Hút)",
            "category": "🎬 Review Phim / TikTok",
            "gender": "Female",
            "base_voice": "vi-VN-HoaiMyNeural",
            "rate_offset": "+18%",
            "pitch": "+3Hz",
            "pause_profile": "movie_review",
            "recommended_translation_style": "movie_review_spoken_vi",
        },
        {
            "id": "vi-VN-NamMinhNeural_tiktok_review",
            "name": "Nam Minh (Review Phim TikTok Kịch Tính)",
            "category": "🎬 Review Phim / TikTok",
            "gender": "Male",
            "base_voice": "vi-VN-NamMinhNeural",
            "rate_offset": "+14%",
            "pitch": "-2Hz",
            "pause_profile": "movie_review",
            "recommended_translation_style": "movie_review_spoken_vi",
        },
        {
            "id": "vi-VN-NamMinhNeural_tiktok_fast",
            "name": "Nam Minh (Review Phim Tốc Độ & Lôi Cuốn)",
            "category": "🎬 Review Phim / TikTok",
            "gender": "Male",
            "base_voice": "vi-VN-NamMinhNeural",
            "rate_offset": "+17%",
            "pitch": "+0Hz",
            "pause_profile": "movie_review",
            "recommended_translation_style": "movie_review_spoken_vi",
        },

        # Nhóm: 🎙️ Truyền Cảm & Kể Chuyện
        {
            "id": "vi-VN-HoaiMyNeural",
            "name": "Hoài My (Nữ - Truyền cảm & Tự nhiên)",
            "category": "🎙️ Truyền Cảm & Kể Chuyện",
            "gender": "Female",
            "base_voice": "vi-VN-HoaiMyNeural",
            "rate_offset": "+10%",
            "pitch": "+0Hz",
            "pause_profile": "standard",
            "recommended_translation_style": "standard_dubbing",
        },
        {
            "id": "vi-VN-HoaiMyNeural_story",
            "name": "Hoài My (Nữ - Thuyết minh & Kể chuyện)",
            "category": "🎙️ Truyền Cảm & Kể Chuyện",
            "gender": "Female",
            "base_voice": "vi-VN-HoaiMyNeural",
            "rate_offset": "+5%",
            "pitch": "-4Hz",
            "pause_profile": "standard",
            "recommended_translation_style": "standard_dubbing",
        },
        {
            "id": "vi-VN-NamMinhNeural",
            "name": "Nam Minh (Nam - Trầm ấm & Tiêu chuẩn)",
            "category": "🎙️ Truyền Cảm & Kể Chuyện",
            "gender": "Male",
            "base_voice": "vi-VN-NamMinhNeural",
            "rate_offset": "+10%",
            "pitch": "+0Hz",
            "pause_profile": "standard",
            "recommended_translation_style": "standard_dubbing",
        },
        {
            "id": "vi-VN-NamMinhNeural_deep",
            "name": "Nam Minh (Nam - Trầm sâu / Phim tài liệu)",
            "category": "🎙️ Truyền Cảm & Kể Chuyện",
            "gender": "Male",
            "base_voice": "vi-VN-NamMinhNeural",
            "rate_offset": "+5%",
            "pitch": "-10Hz",
            "pause_profile": "standard",
            "recommended_translation_style": "standard_dubbing",
        },

        # Nhóm: ⚡ Vlog & Thời Sự
        {
            "id": "vi-VN-HoaiMyNeural_young",
            "name": "Hoài My (Nữ - Trẻ trung & Vlog hiện đại)",
            "category": "⚡ Vlog & Thời Sự",
            "gender": "Female",
            "base_voice": "vi-VN-HoaiMyNeural",
            "rate_offset": "+20%",
            "pitch": "+8Hz",
            "pause_profile": "standard",
            "recommended_translation_style": "natural_commentary",
        },
        {
            "id": "vi-VN-NamMinhNeural_news",
            "name": "Nam Minh (Nam - Thời sự & Dứt khoát)",
            "category": "⚡ Vlog & Thời Sự",
            "gender": "Male",
            "base_voice": "vi-VN-NamMinhNeural",
            "rate_offset": "+22%",
            "pitch": "+4Hz",
            "pause_profile": "standard",
            "recommended_translation_style": "natural_commentary",
        },
        {
            "id": "vi-VN-NamMinhNeural_fast",
            "name": "Nam Minh (Nam - Review Game & Năng động)",
            "category": "⚡ Vlog & Thời Sự",
            "gender": "Male",
            "base_voice": "vi-VN-NamMinhNeural",
            "rate_offset": "+25%",
            "pitch": "+6Hz",
            "pause_profile": "standard",
            "recommended_translation_style": "natural_commentary",
        },
        # Alias giữ backward compatibility
        {
            "id": "vi-VN-HoaiMyNeural_fast",
            "name": "Hoài My (Nữ - Nhịp nhanh)",
            "category": "⚡ Vlog & Thời Sự",
            "gender": "Female",
            "base_voice": "vi-VN-HoaiMyNeural",
            "rate_offset": "+20%",
            "pitch": "+4Hz",
            "pause_profile": "standard",
            "recommended_translation_style": "natural_commentary",
        },
    ],
    "en": [
        {"id": "en-US-JennyNeural", "name": "Jenny (Nữ Mỹ - Tự nhiên)", "category": "🇺🇸 Tiếng Anh", "gender": "Female", "base_voice": "en-US-JennyNeural", "rate_offset": "+10%", "pitch": "+0Hz", "pause_profile": "standard", "recommended_translation_style": "standard_dubbing"},
        {"id": "en-US-GuyNeural", "name": "Guy (Nam Mỹ - Thân thiện)", "category": "🇺🇸 Tiếng Anh", "gender": "Male", "base_voice": "en-US-GuyNeural", "rate_offset": "+10%", "pitch": "+0Hz", "pause_profile": "standard", "recommended_translation_style": "standard_dubbing"},
        {"id": "en-US-AriaNeural", "name": "Aria (Nữ Mỹ - Biểu cảm cao)", "category": "🇺🇸 Tiếng Anh", "gender": "Female", "base_voice": "en-US-AriaNeural", "rate_offset": "+15%", "pitch": "+3Hz", "pause_profile": "standard", "recommended_translation_style": "standard_dubbing"},
        {"id": "en-US-ChristopherNeural", "name": "Christopher (Nam Mỹ - Chuyên nghiệp)", "category": "🇺🇸 Tiếng Anh", "gender": "Male", "base_voice": "en-US-ChristopherNeural", "rate_offset": "+10%", "pitch": "-3Hz", "pause_profile": "standard", "recommended_translation_style": "standard_dubbing"},
        {"id": "en-GB-SoniaNeural", "name": "Sonia (Nữ Anh - Sang trọng)", "category": "🇬🇧 Tiếng Anh (UK)", "gender": "Female", "base_voice": "en-GB-SoniaNeural", "rate_offset": "+10%", "pitch": "+0Hz", "pause_profile": "standard", "recommended_translation_style": "standard_dubbing"},
        {"id": "en-GB-RyanNeural", "name": "Ryan (Nam Anh - Chuẩn mực)", "category": "🇬🇧 Tiếng Anh (UK)", "gender": "Male", "base_voice": "en-GB-RyanNeural", "rate_offset": "+10%", "pitch": "+0Hz", "pause_profile": "standard", "recommended_translation_style": "standard_dubbing"},
    ],
    "zh": [
        {"id": "zh-CN-XiaoxiaoNeural", "name": "Xiaoxiao (Nữ - Truyền cảm)", "category": "🇨🇳 Tiếng Trung", "gender": "Female", "base_voice": "zh-CN-XiaoxiaoNeural", "rate_offset": "+10%", "pitch": "+0Hz", "pause_profile": "standard", "recommended_translation_style": "standard_dubbing"},
        {"id": "zh-CN-YunxiNeural", "name": "Yunxi (Nam - Sống động)", "category": "🇨🇳 Tiếng Trung", "gender": "Male", "base_voice": "zh-CN-YunxiNeural", "rate_offset": "+15%", "pitch": "+0Hz", "pause_profile": "standard", "recommended_translation_style": "standard_dubbing"},
    ],
    "ja": [
        {"id": "ja-JP-NanamiNeural", "name": "Nanami (Nữ - Dễ thương)", "category": "🇯🇵 Tiếng Nhật", "gender": "Female", "base_voice": "ja-JP-NanamiNeural", "rate_offset": "+10%", "pitch": "+0Hz", "pause_profile": "standard", "recommended_translation_style": "standard_dubbing"},
        {"id": "ja-JP-KeitaNeural", "name": "Keita (Nam - Rõ ràng)", "category": "🇯🇵 Tiếng Nhật", "gender": "Male", "base_voice": "ja-JP-KeitaNeural", "rate_offset": "+10%", "pitch": "+0Hz", "pause_profile": "standard", "recommended_translation_style": "standard_dubbing"},
    ],
    "ko": [
        {"id": "ko-KR-SunHiNeural", "name": "Sun-Hi (Nữ - Ngọt ngào)", "category": "🇰🇷 Tiếng Hàn", "gender": "Female", "base_voice": "ko-KR-SunHiNeural", "rate_offset": "+10%", "pitch": "+0Hz", "pause_profile": "standard", "recommended_translation_style": "standard_dubbing"},
        {"id": "ko-KR-InJoonNeural", "name": "In-Joon (Nam - Ấm áp)", "category": "🇰🇷 Tiếng Hàn", "gender": "Male", "base_voice": "ko-KR-InJoonNeural", "rate_offset": "+10%", "pitch": "+0Hz", "pause_profile": "standard", "recommended_translation_style": "standard_dubbing"},
    ],
    "fr": [
        {"id": "fr-FR-DeniseNeural", "name": "Denise (Nữ Pháp)", "category": "🇫🇷 Tiếng Pháp", "gender": "Female", "base_voice": "fr-FR-DeniseNeural", "rate_offset": "+10%", "pitch": "+0Hz", "pause_profile": "standard", "recommended_translation_style": "standard_dubbing"},
        {"id": "fr-FR-HenriNeural", "name": "Henri (Nam Pháp)", "category": "🇫🇷 Tiếng Pháp", "gender": "Male", "base_voice": "fr-FR-HenriNeural", "rate_offset": "+10%", "pitch": "+0Hz", "pause_profile": "standard", "recommended_translation_style": "standard_dubbing"},
    ],
    "es": [
        {"id": "es-ES-ElviraNeural", "name": "Elvira (Nữ TBN)", "category": "🇪🇸 Tiếng TBN", "gender": "Female", "base_voice": "es-ES-ElviraNeural", "rate_offset": "+10%", "pitch": "+0Hz", "pause_profile": "standard", "recommended_translation_style": "standard_dubbing"},
        {"id": "es-ES-AlvaroNeural", "name": "Alvaro (Nam TBN)", "category": "🇪🇸 Tiếng TBN", "gender": "Male", "base_voice": "es-ES-AlvaroNeural", "rate_offset": "+10%", "pitch": "+0Hz", "pause_profile": "standard", "recommended_translation_style": "standard_dubbing"},
    ],
    "de": [
        {"id": "de-DE-KatjaNeural", "name": "Katja (Nữ Đức)", "category": "🇩🇪 Tiếng Đức", "gender": "Female", "base_voice": "de-DE-KatjaNeural", "rate_offset": "+10%", "pitch": "+0Hz", "pause_profile": "standard", "recommended_translation_style": "standard_dubbing"},
        {"id": "de-DE-ConradNeural", "name": "Conrad (Nam Đức)", "category": "🇩🇪 Tiếng Đức", "gender": "Male", "base_voice": "de-DE-ConradNeural", "rate_offset": "+10%", "pitch": "+0Hz", "pause_profile": "standard", "recommended_translation_style": "standard_dubbing"},
    ],
    "ru": [
        {"id": "ru-RU-SvetlanaNeural", "name": "Svetlana (Nữ Nga)", "category": "🇷🇺 Tiếng Nga", "gender": "Female", "base_voice": "ru-RU-SvetlanaNeural", "rate_offset": "+10%", "pitch": "+0Hz", "pause_profile": "standard", "recommended_translation_style": "standard_dubbing"},
        {"id": "ru-RU-DmitryNeural", "name": "Dmitry (Nam Nga)", "category": "🇷🇺 Tiếng Nga", "gender": "Male", "base_voice": "ru-RU-DmitryNeural", "rate_offset": "+10%", "pitch": "+0Hz", "pause_profile": "standard", "recommended_translation_style": "standard_dubbing"},
    ],
    "th": [
        {"id": "th-TH-PremwadeeNeural", "name": "Premwadee (Nữ Thái)", "category": "🇹🇭 Tiếng Thái", "gender": "Female", "base_voice": "th-TH-PremwadeeNeural", "rate_offset": "+10%", "pitch": "+0Hz", "pause_profile": "standard", "recommended_translation_style": "standard_dubbing"},
        {"id": "th-TH-NiwatNeural", "name": "Niwat (Nam Thái)", "category": "🇹🇭 Tiếng Thái", "gender": "Male", "base_voice": "th-TH-NiwatNeural", "rate_offset": "+10%", "pitch": "+0Hz", "pause_profile": "standard", "recommended_translation_style": "standard_dubbing"},
    ],
}


def get_voice_catalog() -> Dict[str, List[Dict[str, Any]]]:
    return VOICE_CATALOG


def get_available_voices(language: str = "vi") -> List[Dict[str, Any]]:
    """
    Lấy danh sách các giọng đọc AI phong phú theo mã ngôn ngữ.
    """
    return VOICE_CATALOG.get(language, VOICE_CATALOG.get("vi", []))


def get_voice_preset_metadata(voice_id: str) -> Dict[str, Any]:
    """
    Lấy thông tin metadata cấu hình đầy đủ của một voice ID.
    """
    for lang_voices in VOICE_CATALOG.values():
        for v in lang_voices:
            if v["id"] == voice_id:
                return dict(v)
    return {
        "id": voice_id,
        "name": voice_id,
        "category": "🎙️ Khác",
        "gender": "Unknown",
        "base_voice": voice_id,
        "rate_offset": "+0%",
        "pitch": "+0Hz",
        "pause_profile": "standard",
        "recommended_translation_style": "standard_dubbing",
    }


def resolve_effective_tts_speed(voice_id: str, user_speed_rate: str = "+0%") -> Dict[str, Any]:
    """
    Phân giải tốc độ tổng hợp Edge-TTS cho Voice Preset và thanh trượt người dùng:
    - preset_rate_offset: Tốc độ cơ sở của preset (ví dụ +15%)
    - user_rate_offset: Tốc độ tinh chỉnh thêm của người dùng (ví dụ +5%)
    - total_rate: Tổng synthesis rate đưa vào Edge-TTS (ví dụ +20%)
    
    LƯU Ý QUAN TRỌNG: Hàm này CHỈ chịu trách nhiệm synthesis rate cho Edge-TTS.
    Tuyệt đối KHÔNG tính toán trước atempo sync speed để tránh hiện tượng double-speed.
    """
    meta = get_voice_preset_metadata(voice_id)
    base_voice = meta.get("base_voice", voice_id)

    rate_offset_str = meta.get("rate_offset", "+0%")
    try:
        rate_offset_val = int(str(rate_offset_str).replace("%", "").replace("+", "").strip() or 0)
    except ValueError:
        rate_offset_val = 0

    try:
        user_rate_val = int(str(user_speed_rate).replace("%", "").replace("+", "").strip() or 0)
    except ValueError:
        user_rate_val = 0

    total_rate = rate_offset_val + user_rate_val
    rate_str = f"+{total_rate}%" if total_rate >= 0 else f"{total_rate}%"
    pitch_str = meta.get("pitch", "+0Hz")
    pause_profile = meta.get("pause_profile", "standard")
    rec_style = meta.get("recommended_translation_style", "standard_dubbing")

    return {
        "voice_id": voice_id,
        "base_voice": base_voice,
        "preset_rate_offset": rate_offset_val,
        "user_rate_offset": user_rate_val,
        "synthesis_rate_percent": total_rate,
        "rate": rate_str,
        "pitch": pitch_str,
        "pause_profile": pause_profile,
        "recommended_translation_style": rec_style,
        "category": meta.get("category", "🎙️ Khác"),
    }


def _resolve_voice_params(voice_id: str, user_speed_rate: str = "+0%") -> Dict[str, str]:
    """
    Phân giải Voice ID thành base_voice, rate và pitch tối ưu cho Edge-TTS synthesis.
    """
    resolved = resolve_effective_tts_speed(voice_id, user_speed_rate)
    return {
        "base_voice": resolved["base_voice"],
        "rate": resolved["rate"],
        "pitch": resolved["pitch"],
    }



def normalize_spoken_text_for_tts(text: str, style: str = "movie_review_spoken_vi") -> str:
    r"""
    Chuẩn hóa văn bản dành riêng cho TTS synthesis (KHÔNG sửa subtitle hiển thị).
    Tối ưu nhịp điệu đọc cho thuyết minh / Review Phim TikTok:
    - Loại bỏ chú thích trong ngoặc [music], (cười)...
    - Collapse duplicate pause markers: '... ...', '……', '....', '. . .', ',,', ', , '
    - Loại bỏ leading continuation ellipsis ở đầu câu ('^(\.{2,}|…|\s|,)+') để Edge-TTS không bị delay im lặng ở đầu audio.
    - Chuyển đổi mid-sentence ellipsis giữa các mệnh đề liên tục sang dấu phẩy ',' để giọng đọc liền mạch, ngắt nghỉ nhẹ (0.10s) thay vì ngắt lặng (0.60s).
    - Bảo lưu suspense ellipsis khi thực sự là kết thúc ý lửng / cliffhanger ở cuối câu ('Có gì đó không ổn...').
    - Chuẩn hóa khoảng trắng và dấu câu.
    """
    if not text:
        return ""

    t = text.strip()

    # 1. Loại bỏ chú thích trong ngoặc [music], (applause)...
    t = re.sub(r"\[.*?\]|\(.*?\)", "", t).strip()

    # 2. Collapse duplicate pause markers & canonicalization
    # '... ...', '...  ...', '……', '....', '. . .'
    t = re.sub(r"\.{4,}", "...", t)
    t = re.sub(r"\.\s*\.\s*\.+", "...", t)
    t = re.sub(r"…+", "...", t)
    t = re.sub(r"(\.{3,}|…)(?:\s*(\.{3,}|…))+", "...", t)
    t = re.sub(r",\s*,+", ",", t)
    t = re.sub(r"\?{2,}", "?", t)
    t = re.sub(r"\!{2,}", "!", t)
    t = re.sub(r"(\.{3,}|…)\s*,\s*", ", ", t)
    t = re.sub(r",\s*(\.{3,}|…)", ", ", t)
    t = re.sub(r"[,;:]\s*[,;:]+", ",", t)

    # 3. Loại bỏ leading continuation markers ở đầu câu
    # Ví dụ: '...tiếp tục sinh tồn ở màn này không?' -> 'tiếp tục sinh tồn ở màn này không?'
    t = re.sub(r"^(\.{2,}|…|\s|,)+", "", t).strip()

    # 4. Xử lý mid-sentence ellipsis cho phong cách review / spoken commentary
    # Khi '...' xuất hiện ở giữa câu (theo sau bởi chữ cái, từ nối, hoặc dấu ngoặc trích dẫn mà không phải hết câu):
    # Ví dụ Case A: 'Thế nhưng điều nguy hiểm là... ngay trên hòn đảo' -> 'Thế nhưng điều nguy hiểm là, ngay trên hòn đảo'
    # Ví dụ Case C: 'Giờ tôi mới hiểu... câu' -> 'Giờ tôi mới hiểu, câu'
    # Ví dụ Case D: 'nhất định... ...phải chế' -> 'nhất định, phải chế'
    if style in {"movie_review_spoken_vi", "natural_commentary", "movie_review"}:
        # Thay thế mid-sentence ellipsis giữa các từ thành dấu phẩy
        t = re.sub(r"(?<=[\w\d\"\'\)])\s*(?:\.{3,}|…)\s*(?=[\w\d\"\'\(])", ", ", t)

    # 5. Đảm bảo dấu câu đơn lẻ có khoảng trắng theo sau hợp lệ (không tách dấu ba chấm '...')
    t = re.sub(r"(?<!\.)([,:;?!])(?=[^\s\d\"\'\)])", r"\1 ", t)
    t = re.sub(r"(?<!\.)\.(?!\.)(?=[^\s\d\"\'\)])", r". ", t)
    t = re.sub(r"(\.{3,}|…)(?=[^\s\"\'\)])", r"\1 ", t)

    # 6. Dọn dẹp khoảng trắng thừa và dấu phẩy trùng
    t = re.sub(r",\s*,+", ",", t)
    t = re.sub(r"\s+", " ", t).strip()

    return t


def clean_text_for_tts(text: str, style: str = "movie_review_spoken_vi") -> str:
    """
    Làm sạch và tối ưu hóa văn bản để giọng đọc ngắt câu tự nhiên, không bị vấp.
    """
    return normalize_spoken_text_for_tts(text, style=style)


class BaseTTSProvider(ABC):
    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: str,
        output_file: Path,
        speed_rate: str = "+0%",
        pitch: Optional[str] = None,
        style: str = "movie_review_spoken_vi",
        max_retries: int = 3,
        attempt_callback: Optional[Any] = None,
    ) -> Path:
        pass


from backend.utils.retry_utils import is_recoverable_error


class EdgeTTSProvider(BaseTTSProvider):
    async def synthesize(
        self,
        text: str,
        voice: str,
        output_file: Path,
        speed_rate: str = "+0%",
        pitch: Optional[str] = None,
        style: str = "movie_review_spoken_vi",
        max_retries: int = 3,
        attempt_callback=None,
    ) -> Path:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        # 1. Tận dụng cache nếu file đã tồn tại và hợp lệ (>= MIN_VALID_AUDIO_BYTES)
        if output_file.exists() and output_file.stat().st_size >= MIN_VALID_AUDIO_BYTES:
            return output_file

        params = _resolve_voice_params(voice, speed_rate)
        if pitch is not None:
            params["pitch"] = pitch

        clean_text = clean_text_for_tts(text, style=style)
        if not clean_text:
            clean_text = "..."

        last_error = None
        backoff_delays = [1.0, 2.0, 4.0]

        for attempt in range(1, max_retries + 1):
            if attempt > 1 and attempt_callback:
                try:
                    await attempt_callback(attempt, max_retries, last_error)
                except Exception:
                    pass

            try:
                communicate = edge_tts.Communicate(
                    text=clean_text,
                    voice=params["base_voice"],
                    rate=params["rate"],
                    pitch=params["pitch"],
                )
                # Đặt timeout từ config (TTS_REQUEST_TIMEOUT) cho mỗi lần giao tiếp EdgeTTS để tránh treo vô tận
                await asyncio.wait_for(communicate.save(str(output_file.resolve())), timeout=TTS_REQUEST_TIMEOUT)
                if output_file.exists() and output_file.stat().st_size >= MIN_VALID_AUDIO_BYTES:
                    if attempt > 1 and attempt_callback:
                        try:
                            await attempt_callback(attempt, max_retries, None, recovered=True)
                        except Exception:
                            pass
                    return output_file
                else:
                    # File sinh ra bị rỗng hoặc nhỏ bất thường -> dọn dẹp và thử lại
                    if output_file.exists():
                        output_file.unlink(missing_ok=True)
                    raise RuntimeError(f"FILE_CORRUPTED_OR_TOO_SMALL: Kích thước file audio < {MIN_VALID_AUDIO_BYTES} bytes")
            except Exception as e:
                last_error = e
                logger.warning(f"Lỗi Edge-TTS lần {attempt}/{max_retries} cho text '{clean_text[:30]}...': {e}")
                if output_file.exists() and output_file.stat().st_size < MIN_VALID_AUDIO_BYTES:
                    output_file.unlink(missing_ok=True)

                if not is_recoverable_error(e) and not isinstance(e, (asyncio.TimeoutError, TimeoutError)):
                    logger.warning(f"Lỗi Edge-TTS không thể phục hồi: {e}")
                    raise e

                if attempt < max_retries:
                    wait_sec = backoff_delays[min(attempt - 1, len(backoff_delays) - 1)]
                    await asyncio.sleep(wait_sec)

        raise RuntimeError(f"EDGE_TTS_TEMPORARY_FAILURE: Thất bại sau {max_retries} lần thử: {last_error}")


_DEFAULT_PROVIDER: BaseTTSProvider = EdgeTTSProvider()


def get_voices_for_language(lang_code: str) -> List[Dict[str, Any]]:
    code = lang_code.lower()
    if code in VOICE_CATALOG:
        return VOICE_CATALOG[code]
    return VOICE_CATALOG.get("en", [])


get_available_voices = get_voices_for_language


async def generate_speech_segment(
    text: str,
    voice: str,
    output_path: Optional[Path] = None,
    speed_rate: str = "+0%",
    provider: Optional[BaseTTSProvider] = None,
    *,
    output_audio_path: Optional[Path] = None,
    rate: Optional[str] = None,
) -> Path:
    out_file = output_path or output_audio_path
    if not out_file:
        raise ValueError("Thiếu đường dẫn file audio đầu ra.")
    actual_rate = rate if rate is not None else speed_rate
    p = provider or _DEFAULT_PROVIDER
    return await p.synthesize(text=text, voice=voice, output_file=out_file, speed_rate=actual_rate)


generate_speech_for_text = generate_speech_segment


async def generate_all_segments(
    segments: List[Dict[str, Any]],
    voice: str,
    tts_dir: Path,
    speed_rate: str = "+0%",
    provider: Optional[BaseTTSProvider] = None,
    concurrency_limit: int = TTS_CONCURRENCY,
    progress_callback=None,
    force_regenerate: bool = False,
) -> List[Dict[str, Any]]:
    """
    Tổng hợp audio cho toàn bộ SpeechChunks hỗ trợ Item-Level Checkpoint & Resume:
    - Zero-Byte File Cleaner & Reconcile: Xóa sạch file < 200 bytes khi bắt đầu.
    - Fast Checkpoint Validation: Scan toàn bộ file trong < 5ms.
    - Chunk đã có file hợp lệ (>= 200 bytes) được tái sử dụng 100% (KHÔNG gọi mạng, KHÔNG rewrite đĩa).
    - Incremental Atomic Checkpoint Flush: Sau mỗi chunk (thành công hoặc thất bại), ghi atomic tts_chunks_state.json và gọi callback.
    - Realtime Active Chunks Heartbeat: Báo cáo danh sách chunk đang chạy đồng thời.
    """
    tts_dir.mkdir(parents=True, exist_ok=True)
    p = provider or _DEFAULT_PROVIDER
    semaphore = asyncio.Semaphore(concurrency_limit)
    total_count = len(segments)
    lock = asyncio.Lock()
    active_chunk_indices: Set[int] = set()

    # 1. Zero-Byte & Corrupted File Cleaner on Start (Invariant 2)
    if not force_regenerate and tts_dir.exists():
        for f in tts_dir.glob("segment_*.mp3"):
            try:
                if f.stat().st_size < MIN_VALID_AUDIO_BYTES:
                    f.unlink(missing_ok=True)
                    logger.info(f"[TTS Cleaner] Đã dọn dẹp file MP3 rỗng/hỏng: {f.name}")
            except Exception:
                pass

    # 2. Nạp checkpoint cũ nếu có
    checkpoint_file = tts_dir / "tts_chunks_state.json"
    chunk_states: Dict[str, Dict[str, Any]] = {}
    if checkpoint_file.exists() and not force_regenerate:
        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                chunk_states = json.load(f)
        except Exception:
            chunk_states = {}

    meta = get_voice_preset_metadata(voice)
    resolved = resolve_effective_tts_speed(voice, speed_rate)
    voice_pitch = resolved.get("pitch", "+0Hz")
    preset_style = meta.get("recommended_translation_style", "movie_review_spoken_vi")

    # 3. Phân loại ngay lập tức: Reused Chunks vs Pending/Retry Chunks (< 5ms)
    reused_results: List[Dict[str, Any]] = []
    pending_segments: List[Dict[str, Any]] = []

    for seg in segments:
        idx = seg["index"]
        idx_key = str(idx)
        raw_display_text = (seg.get("translated_text") or seg.get("original_text") or "").strip()
        seg_file = tts_dir / f"segment_{idx:04d}.mp3"

        if not raw_display_text:
            chunk_states[idx_key] = {"index": idx, "status": "skipped", "text": "", "file_path": None}
            continue

        chunk_style = seg.get("translation_style") or preset_style
        spoken_text = normalize_spoken_text_for_tts(raw_display_text, style=chunk_style)
        trans_rev = int(seg.get("translation_revision") or 1)

        chunk_sig = compute_tts_chunk_signature(
            voice=voice,
            speed_rate=speed_rate,
            text=spoken_text,
            pitch=voice_pitch,
            translation_rev=trans_rev,
            norm_version="v2_pause_norm",
        )
        saved_sig = chunk_states.get(idx_key, {}).get("config_signature")
        saved_voice = chunk_states.get(idx_key, {}).get("voice")

        # Kiểm tra config_signature và file thật trên ổ đĩa (>= MIN_VALID_AUDIO_BYTES)
        is_signature_valid = (saved_sig == chunk_sig) or (saved_sig is None and (saved_voice is None or saved_voice == voice))
        can_reuse = not force_regenerate and is_signature_valid and seg_file.exists() and seg_file.stat().st_size >= MIN_VALID_AUDIO_BYTES

        if can_reuse:
            seg_start = float(seg.get("start", 0.0))
            seg_end = float(seg.get("end", seg_start + 2.0))
            seg_dur = float(seg.get("duration", round(seg_end - seg_start, 2)))
            reused_results.append({
                "index": idx,
                "phrase_id": seg.get("phrase_id", idx),
                "start": seg_start,
                "end": seg_end,
                "duration": seg_dur,
                "text": raw_display_text,
                "display_text": raw_display_text,
                "spoken_text": spoken_text,
                "file_path": str(seg_file),
                "punctuation_end": seg.get("punctuation_end", ""),
                "is_complete_sentence": seg.get("is_complete_sentence", False),
                "original_text": seg.get("original_text", ""),
                "original_whisper_indices": seg.get("original_whisper_indices", []),
                "source_chunks": seg.get("source_chunks", [idx]),
                "member_count": seg.get("member_count", 1),
                "reused": True,
            })
            chunk_states[idx_key] = {
                "index": idx,
                "status": "completed",
                "attempts": chunk_states.get(idx_key, {}).get("attempts", 1),
                "file_path": str(seg_file),
                "config_signature": chunk_sig,
                "voice": voice,
                "speed_rate": speed_rate,
                "pitch": voice_pitch,
                "reused": True,
            }
        else:
            if seg_file.exists() and (not is_signature_valid or seg_file.stat().st_size < MIN_VALID_AUDIO_BYTES):
                seg_file.unlink(missing_ok=True)
            pending_segments.append(seg)

    completed_count = len(reused_results)
    reused_count = len(reused_results)
    pending_count = len(pending_segments)

    logger.info(
        f"[TTS Resume] Tổng {total_count} chunks: Tái sử dụng {reused_count} chunks hợp lệ, "
        f"cần tổng hợp/retry {pending_count} chunks."
    )

    # 4. Báo cáo tiến độ ngay lập tức với số chunk đã reuse
    if progress_callback:
        if pending_count > 0:
            msg = f"Đã tái sử dụng {reused_count}/{total_count} SpeechChunks. Đang xử lý {pending_count} đoạn còn lại..."
        else:
            msg = f"Đã tái sử dụng toàn bộ {reused_count}/{total_count} SpeechChunks."
        extra_initial = {
            "completed_chunks": completed_count,
            "total_chunks": total_count,
            "active_chunks": [],
            "failed_chunks": 0,
            "last_progress_at": _iso_now(),
        }
        try:
            await progress_callback(completed_count, total_count, message=msg, extra=extra_initial)
        except TypeError:
            try:
                await progress_callback(completed_count, total_count, message=msg)
            except TypeError:
                await progress_callback(completed_count, total_count)
        except Exception:
            pass

    # Nếu tất cả đã có sẵn -> lưu atomic checkpoint và trả về ngay lập tức
    if pending_count == 0:
        save_tts_checkpoint_atomic(checkpoint_file, chunk_states)
        return sorted(reused_results, key=lambda x: x["index"])

    # 5. Chỉ thực thi tổng hợp cho pending_segments (Zero Stagger Delay cho retry item đầu tiên)
    generated_results: List[Dict[str, Any]] = []

    async def _synthesize_pending_segment(seg: Dict[str, Any], queue_idx: int) -> Optional[Dict[str, Any]]:
        nonlocal completed_count
        idx = seg["index"]
        idx_key = str(idx)
        raw_display_text = (seg.get("translated_text") or seg.get("original_text") or "").strip()
        chunk_style = seg.get("translation_style") or preset_style
        spoken_text = normalize_spoken_text_for_tts(raw_display_text, style=chunk_style)
        trans_rev = int(seg.get("translation_revision") or 1)
        seg_file = tts_dir / f"segment_{idx:04d}.mp3"
        chunk_sig = compute_tts_chunk_signature(
            voice=voice,
            speed_rate=speed_rate,
            text=spoken_text,
            pitch=voice_pitch,
            translation_rev=trans_rev,
            norm_version="v2_pause_norm",
        )

        # Stagger nhỏ (0.05s) CHỈ áp dụng giữa các task trong pending queue
        stagger_delay = min(1.0, queue_idx * 0.05)
        if stagger_delay > 0:
            await asyncio.sleep(stagger_delay)

        async def _attempt_reporter(attempt: int, max_att: int, last_err: Optional[Exception] = None, recovered: bool = False):
            if progress_callback:
                if recovered:
                    cur_msg = f"✓ Đã khôi phục chunk #{idx}. Đang tiếp tục xử lý ({completed_count}/{total_count})..."
                else:
                    cur_msg = f"Lỗi tạm thời ở chunk #{idx}. Đang tự thử lại lần {attempt}/{max_att} ({completed_count}/{total_count} hoàn thành)..."
                try:
                    await progress_callback(completed_count, total_count, message=cur_msg)
                except TypeError:
                    await progress_callback(completed_count, total_count)
                except Exception:
                    pass

        async with semaphore:
            async with lock:
                active_chunk_indices.add(idx)

            try:
                try:
                    await p.synthesize(
                        text=spoken_text,
                        voice=voice,
                        output_file=seg_file,
                        speed_rate=speed_rate,
                        pitch=voice_pitch,
                        style=chunk_style,
                        attempt_callback=_attempt_reporter,
                    )
                except TypeError:
                    await p.synthesize(
                        text=spoken_text,
                        voice=voice,
                        output_file=seg_file,
                        speed_rate=speed_rate,
                    )
                seg_start = float(seg.get("start", 0.0))
                seg_end = float(seg.get("end", seg_start + 2.0))
                seg_dur = float(seg.get("duration", round(seg_end - seg_start, 2)))
                res = {
                    "index": idx,
                    "phrase_id": seg.get("phrase_id", idx),
                    "start": seg_start,
                    "end": seg_end,
                    "duration": seg_dur,
                    "text": raw_display_text,
                    "display_text": raw_display_text,
                    "spoken_text": spoken_text,
                    "file_path": str(seg_file),
                    "punctuation_end": seg.get("punctuation_end", ""),
                    "is_complete_sentence": seg.get("is_complete_sentence", False),
                    "original_text": seg.get("original_text", ""),
                    "original_whisper_indices": seg.get("original_whisper_indices", []),
                    "source_chunks": seg.get("source_chunks", [idx]),
                    "member_count": seg.get("member_count", 1),
                    "reused": False,
                }
                status_item = {
                    "index": idx,
                    "status": "completed",
                    "attempts": chunk_states.get(idx_key, {}).get("attempts", 0) + 1,
                    "file_path": str(seg_file),
                    "config_signature": chunk_sig,
                    "voice": voice,
                    "speed_rate": speed_rate,
                    "pitch": voice_pitch,
                    "error_message": None,
                }
            except Exception as e:
                logger.error(f"Lỗi sinh audio cho segment #{idx}: {e}")
                res = None
                status_item = {
                    "index": idx,
                    "status": "failed",
                    "attempts": chunk_states.get(idx_key, {}).get("attempts", 0) + 1,
                    "file_path": None,
                    "error_message": str(e),
                }
            finally:
                async with lock:
                    active_chunk_indices.discard(idx)
                    if res is not None:
                        completed_count += 1
                    chunk_states[idx_key] = status_item

                    # ATOMIC CHECKPOINT FLUSH ON EVERY CHUNK (Invariant 3)
                    save_tts_checkpoint_atomic(checkpoint_file, chunk_states)

                    if progress_callback:
                        cur_pct = round((completed_count / max(1, total_count)) * 100.0, 1)
                        active_list = sorted(list(active_chunk_indices))
                        if active_list:
                            active_str = ", ".join(f"#{i}" for i in active_list[:4])
                            if len(active_list) > 4:
                                active_str += f" (+{len(active_list)-4} đoạn)"
                            cur_msg = f"Đang tổng hợp {completed_count}/{total_count} SpeechChunks ({cur_pct}%) - Đang xử lý: {active_str}"
                        else:
                            cur_msg = f"Đang tổng hợp {completed_count}/{total_count} SpeechChunks ({cur_pct}%) - Xong chunk #{idx}"

                        failed_count = len([v for v in chunk_states.values() if v.get("status") == "failed"])
                        extra_info = {
                            "completed_chunks": completed_count,
                            "total_chunks": total_count,
                            "active_chunks": active_list,
                            "failed_chunks": failed_count,
                            "last_progress_at": _iso_now(),
                        }
                        try:
                            await progress_callback(completed_count, total_count, message=cur_msg, extra=extra_info)
                        except TypeError:
                            try:
                                await progress_callback(completed_count, total_count, message=cur_msg)
                            except TypeError:
                                await progress_callback(completed_count, total_count)
                        except Exception:
                            pass

            return res

    tasks = [_synthesize_pending_segment(seg, k) for k, seg in enumerate(pending_segments)]
    raw_results = await asyncio.gather(*tasks)
    for r in raw_results:
        if r is not None:
            generated_results.append(r)

    # 6. Final atomic checkpoint flush
    save_tts_checkpoint_atomic(checkpoint_file, chunk_states)

    failed_chunks = [v for v in chunk_states.values() if v.get("status") == "failed"]
    if failed_chunks:
        first_fail = failed_chunks[0]
        total_done = len(reused_results) + len(generated_results)
        raise RuntimeError(
            f"TTS_CHUNK_FAILED: Lỗi tổng hợp tại chunk #{first_fail.get('index')} "
            f"({total_done}/{total_count} hoàn thành): {first_fail.get('error_message')}"
        )

    all_results = reused_results + generated_results
    logger.info(f"Đã hoàn thành toàn bộ {len(all_results)}/{total_count} audio segments (Reused: {reused_count}, Generated: {len(generated_results)}).")
    return sorted(all_results, key=lambda x: x["index"])

