import asyncio
import json
import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
import edge_tts

logger = logging.getLogger("tts_service")

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



def clean_text_for_tts(text: str) -> str:
    """
    Làm sạch và tối ưu hóa văn bản để giọng đọc ngắt câu tự nhiên, không bị vấp.
    """
    t = text.strip()
    # Loại bỏ dấu ngoặc vuông chú thích [music], (applause)...
    t = re.sub(r"\[.*?\]|\(.*?\)", "", t)
    # Chuẩn hóa dấu chấm câu lặp lại
    t = re.sub(r"\.{2,}", "...", t)
    t = re.sub(r"\?{2,}", "?", t)
    t = re.sub(r"\!{2,}", "!", t)
    # Đảm bảo có khoảng trắng sau dấu câu
    t = re.sub(r"([,.:;?!])(?=[^\s\d])", r"\1 ", t)
    # Loại bỏ khoảng trắng thừa
    t = re.sub(r"\s+", " ", t).strip()
    return t


class BaseTTSProvider(ABC):
    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: str,
        output_file: Path,
        speed_rate: str = "+0%",
    ) -> Path:
        pass


class EdgeTTSProvider(BaseTTSProvider):
    async def synthesize(
        self,
        text: str,
        voice: str,
        output_file: Path,
        speed_rate: str = "+0%",
        max_retries: int = 3,
    ) -> Path:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        # 1. Tận dụng cache nếu file đã tồn tại và hợp lệ
        if output_file.exists() and output_file.stat().st_size > 200:
            return output_file

        params = _resolve_voice_params(voice, speed_rate)
        clean_text = clean_text_for_tts(text)
        if not clean_text:
            clean_text = "..."

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                communicate = edge_tts.Communicate(
                    text=clean_text,
                    voice=params["base_voice"],
                    rate=params["rate"],
                    pitch=params["pitch"],
                )
                # Đặt timeout 20s cho mỗi lần giao tiếp EdgeTTS để tránh treo vô tận
                await asyncio.wait_for(communicate.save(str(output_file.resolve())), timeout=20.0)
                if output_file.exists() and output_file.stat().st_size > 0:
                    return output_file
            except Exception as e:
                last_error = e
                logger.warning(f"Lỗi Edge-TTS lần {attempt}/{max_retries} cho text '{clean_text[:30]}...': {e}")
                if output_file.exists() and output_file.stat().st_size == 0:
                    output_file.unlink(missing_ok=True)
                await asyncio.sleep(0.8 * attempt)

        raise RuntimeError(f"Edge-TTS thất bại sau {max_retries} lần thử: {last_error}")


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
    concurrency_limit: int = 4,
    progress_callback=None,
    force_regenerate: bool = False,
) -> List[Dict[str, Any]]:
    """
    Tổng hợp audio cho toàn bộ SpeechChunks hỗ trợ Item-Level Checkpoint & Resume:
    - Nếu chunk đã được sinh và file segment_XXXX.mp3 hợp lệ (> 0 bytes), tái sử dụng ngay lập tức mà không gọi mạng.
    - Lưu trạng thái chi tiết từng chunk vào tts_chunks_state.json để hỗ trợ retry chính xác từ đoạn bị lỗi.
    """
    tts_dir.mkdir(parents=True, exist_ok=True)
    p = provider or _DEFAULT_PROVIDER
    semaphore = asyncio.Semaphore(concurrency_limit)
    completed_count = 0
    total_count = len(segments)
    lock = asyncio.Lock()

    # Nạp checkpoint cũ nếu có
    checkpoint_file = tts_dir / "tts_chunks_state.json"
    chunk_states: Dict[str, Dict[str, Any]] = {}
    if checkpoint_file.exists() and not force_regenerate:
        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                chunk_states = json.load(f)
        except Exception:
            chunk_states = {}

    async def _process_single_segment(seg: Dict[str, Any], delay_stagger: float = 0.0) -> Optional[Dict[str, Any]]:
        nonlocal completed_count
        idx = seg["index"]
        text_to_speak = (seg.get("translated_text") or seg.get("original_text") or "").strip()
        seg_file = tts_dir / f"segment_{idx:04d}.mp3"
        idx_key = str(idx)

        if not text_to_speak:
            async with lock:
                completed_count += 1
                chunk_states[idx_key] = {"index": idx, "status": "skipped", "text": "", "file_path": None}
                if progress_callback:
                    await progress_callback(completed_count, total_count)
            return None

        # 1. Kiểm tra tái sử dụng chunk hợp lệ nếu đã tồn tại trên ổ đĩa
        if not force_regenerate and seg_file.exists() and seg_file.stat().st_size > 0:
            res = {
                "index": idx,
                "start": seg["start"],
                "end": seg["end"],
                "duration": seg.get("duration", round(seg["end"] - seg["start"], 2)),
                "text": text_to_speak,
                "file_path": str(seg_file),
                "punctuation_end": seg.get("punctuation_end", ""),
                "is_complete_sentence": seg.get("is_complete_sentence", False),
                "original_text": seg.get("original_text", ""),
                "original_whisper_indices": seg.get("original_whisper_indices", []),
                "reused": True,
            }
            async with lock:
                completed_count += 1
                chunk_states[idx_key] = {
                    "index": idx,
                    "status": "completed",
                    "attempts": chunk_states.get(idx_key, {}).get("attempts", 1),
                    "file_path": str(seg_file),
                    "reused": True,
                }
                if progress_callback:
                    await progress_callback(completed_count, total_count)
            return res

        # 2. Tổng hợp chunk mới qua TTS Provider
        if delay_stagger > 0:
            await asyncio.sleep(delay_stagger)

        async with semaphore:
            try:
                await p.synthesize(text=text_to_speak, voice=voice, output_file=seg_file, speed_rate=speed_rate)
                res = {
                    "index": idx,
                    "start": seg["start"],
                    "end": seg["end"],
                    "duration": seg.get("duration", round(seg["end"] - seg["start"], 2)),
                    "text": text_to_speak,
                    "file_path": str(seg_file),
                    "punctuation_end": seg.get("punctuation_end", ""),
                    "is_complete_sentence": seg.get("is_complete_sentence", False),
                    "original_text": seg.get("original_text", ""),
                    "original_whisper_indices": seg.get("original_whisper_indices", []),
                    "reused": False,
                }
                status_item = {
                    "index": idx,
                    "status": "completed",
                    "attempts": chunk_states.get(idx_key, {}).get("attempts", 0) + 1,
                    "file_path": str(seg_file),
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

            async with lock:
                completed_count += 1
                chunk_states[idx_key] = status_item
                if progress_callback:
                    try:
                        await progress_callback(completed_count, total_count)
                    except Exception:
                        pass
            return res

    # Phân tán khởi tạo kết nối (stagger) 0.04s giữa các tác vụ để chống rate-limit
    tasks = [_process_single_segment(seg, i * 0.04) for i, seg in enumerate(segments)]
    raw_results = await asyncio.gather(*tasks)
    results = [r for r in raw_results if r is not None]

    # Lưu checkpoint ra file tts_chunks_state.json
    try:
        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(chunk_states, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Không thể lưu checkpoint TTS: {e}")

    failed_chunks = [v for v in chunk_states.values() if v.get("status") == "failed"]
    if failed_chunks:
        first_fail = failed_chunks[0]
        raise RuntimeError(
            f"TTS_CHUNK_FAILED: Lỗi tổng hợp tại chunk #{first_fail.get('index')} "
            f"({len(results)}/{len(segments)} hoàn thành): {first_fail.get('error_message')}"
        )

    logger.info(f"Đã sinh hoàn tất {len(results)}/{len(segments)} audio segments.")
    return sorted(results, key=lambda x: x["index"])

