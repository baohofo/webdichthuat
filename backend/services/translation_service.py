import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import aiofiles
import httpx
from google import genai
from google.genai import types

from backend.config import GEMINI_API_KEY

logger = logging.getLogger("translation_service")

# Danh sách ngôn ngữ hỗ trợ
LANGUAGE_NAMES = {
    "vi": "Vietnamese",
    "en": "English",
    "zh": "Chinese (Simplified)",
    "ja": "Japanese",
    "ko": "Korean",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "ru": "Russian",
    "th": "Thai",
}

# Mô hình đã được xác nhận hoạt động (được cache lại sau batch đầu tiên thành công)
_CONFIRMED_WORKING_MODEL: Optional[str] = None


def _get_api_key(api_key: Optional[str] = None) -> str:
    from backend.utils.credential_store import get_gemini_api_key_sync
    saved_key = get_gemini_api_key_sync()
    key = (api_key or "").strip() or (saved_key or "").strip() or (GEMINI_API_KEY or "").strip()
    if not key:
        raise ValueError(
            "Chưa cấu hình Gemini API Key! Vui lòng nhập API Key trên giao diện hoặc cấu hình trong Settings."
        )
    return key


def _extract_json_translations(raw_text: str) -> Dict[int, str]:
    """
    Trích xuất mảng JSON từ phản hồi của Gemini, loại bỏ markdown nếu có.
    """
    text = raw_text.strip()
    
    # Loại bỏ code blocks ```json ... ``` nếu có
    if "```" in text:
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
        text = text.strip()

    # Tìm khối JSON array [ ... ]
    match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
    if match:
        text = match.group(0)

    data = json.loads(text)
    translations: Dict[int, str] = {}
    for item in data:
        idx = int(item.get("index", 0))
        translated_text = str(item.get("translated_text", "")).strip()
        if idx > 0 and translated_text:
            translations[idx] = translated_text

    return translations


def _discover_account_models(api_key: str, sdk_client: Optional[genai.Client] = None) -> List[str]:
    """
    Tự động truy vấn danh sách các mô hình Gemini đang hoạt động và được cấp quyền trên tài khoản của người dùng.
    """
    discovered = []

    # 1. Thử lấy qua SDK
    if sdk_client:
        try:
            for m in sdk_client.models.list():
                m_name = getattr(m, "name", "") or ""
                clean_name = m_name.replace("models/", "")
                if "gemini" in clean_name.lower():
                    discovered.append(clean_name)
            if discovered:
                logger.info(f"✓ Đã phát hiện {len(discovered)} model từ SDK: {discovered[:6]}")
                return discovered
        except Exception as e:
            logger.warning(f"SDK list models không thành công: {e}")

    # 2. Thử lấy qua REST API
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        with httpx.Client(timeout=10) as client:
            res = client.get(url)
            if res.status_code == 200:
                data = res.json()
                for m in data.get("models", []):
                    m_name = m.get("name", "").replace("models/", "")
                    methods = m.get("supportedGenerationMethods", [])
                    if "generateContent" in methods or "gemini" in m_name:
                        discovered.append(m_name)
                if discovered:
                    logger.info(f"✓ Đã phát hiện {len(discovered)} model từ REST: {discovered[:6]}")
                    return discovered
    except Exception as e:
        logger.warning(f"REST list models không thành công: {e}")

    # Danh sách dự phòng nếu không list được
    return [
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash-8b",
        "gemini-1.5-pro",
        "gemini-2.0-flash-exp",
    ]


def _call_gemini_rest(
    api_key: str,
    model_name: str,
    prompt: str,
    timeout: int = 60,
) -> str:
    """
    Gọi trực tiếp Gemini REST API (Fallback đáng tin cậy 100% cho mọi định dạng key).
    """
    clean_model = model_name.replace("models/", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={api_key}"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
        }
    }

    with httpx.Client(timeout=timeout) as client:
        res = client.post(url, json=payload)
        if res.status_code != 200:
            raise RuntimeError(f"HTTP {res.status_code}: {res.text}")

        res_data = res.json()
        candidates = res_data.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"Không có nội dung trả về: {res.text}")
        
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            raise RuntimeError(f"Nội dung parts rỗng: {res.text}")
        
        return parts[0].get("text", "")


def _build_style_prompt_instructions(translation_style: str, source_lang_name: str, target_lang_name: str) -> str:
    """
    Xây dựng chỉ dẫn phong cách dịch thuật chuyên biệt theo từng thể loại nội dung.
    """
    if translation_style == "movie_review_spoken_vi":
        return f"""You are an expert video dubbing narrator specializing in high-energy, suspenseful, and punchy movie review commentary for TikTok, Reels, and YouTube Shorts.
Translate the following video transcript items from {source_lang_name} into dramatic, spoken {target_lang_name}.

CRITICAL GUIDELINES FOR TIKTOK MOVIE REVIEW SPOKEN STYLE:
1. Maintain the exact same number of items and matching 'index'.
2. DRAMATIC & FAST-PACED SPOKEN STYLE (PHONG CÁCH REVIEW PHIM TIKTOK KỊCH TÍNH & CUỐN HÚT):
   - Translate specifically for fast-paced, engaging short-form video commentary.
   - Use punchy, gripping, conversational phrases that hook the audience (e.g., "Không ngờ rằng...", "Ngay lúc này...", "Hóa ra là...", "Và rồi điều kinh hoàng đã xảy ra...").
   - Eliminate filler words and stiff written syntax. Sentences must be snappy, rhythmic, and ready for rapid voice-over.
3. DURATION-AWARE & NATURAL COMPACTNESS (TỐI ƯU ĐỘ DÀI & ĐỘ CÔ ĐỌNG THEO THỜI LƯỢNG):
   - Each item includes a 'duration' (seconds). Ensure the Vietnamese sentence can be spoken smoothly within approximately that duration.
   - Prioritize concise, vivid expressions over wordy literal translations.
   - Preserve all crucial facts, proper names, and core message. DO NOT hallucinate or fabricate events.
4. FORMAT:
   - Return ONLY a valid JSON array of objects with 'index' (integer) and 'translated_text' (string). No markdown, notes, or extra commentary.
"""
    elif translation_style == "natural_commentary":
        return f"""You are an expert video dubbing and subtitle translator specializing in high-energy, natural spoken commentary (video game review / vlog commentary style).
Translate the following video transcript items from {source_lang_name} into natural, spoken {target_lang_name}.

CRITICAL GUIDELINES FOR SPOKEN COMMENTARY:
1. Maintain the exact same number of items and matching 'index'.
2. NATURAL COMMENTARY STYLE (VĂN PHONG BÌNH LUẬN / THUYẾT MINH NĂNG ĐỘNG):
   - Translate for conversational voice-over / dubbing, NOT formal academic written text.
   - Use direct, lively, punchy phrasing (e.g., "Nhưng vấn đề là...", "Và tiếp theo...", "Chính vì thế...").
   - Sentences must sound energetic, rhythmic, and easy to speak aloud fluently.
3. DURATION-AWARE & NATURAL COMPACTNESS:
   - Each item includes a 'duration' (seconds). Ensure the sentence fits naturally within approximately that duration.
   - Concise, natural expressions over wordy literal translations.
   - Preserve all core facts, game terms, and meaning.
4. FORMAT:
   - Return ONLY a valid JSON array of objects with 'index' (integer) and 'translated_text' (string). No markdown, notes, or extra commentary.
"""
    else:  # standard_dubbing (default)
        return f"""You are an expert video dubbing and subtitle translator specializing in natural, expressive, and fluent spoken dubbing.
Translate the following video transcript items from {source_lang_name} into natural, spoken {target_lang_name}.

CRITICAL GUIDELINES FOR SPOKEN DUBBING:
1. Maintain the exact same number of items and matching 'index'.
2. NATURAL SPOKEN DUBBING STYLE (VĂN PHONG LỒNG TIẾNG TỰ NHIÊN):
   - Translate specifically for voice-over / dubbing, natural spoken syntax and smooth flow.
   - Clear, articulate, emotionally fitting expressions.
3. DURATION-AWARE & NATURAL COMPACTNESS:
   - Each item includes a 'duration' (seconds). Ensure the sentence can be spoken comfortably within approximately that duration.
   - Preserve all facts, nuances, proper names, and core message.
4. FORMAT:
   - Return ONLY a valid JSON array of objects with 'index' (integer) and 'translated_text' (string). No markdown, notes, or extra commentary.
"""


def _translate_batch_sync(
    api_key: str,
    batch_items: List[Dict[str, Any]],
    source_lang_name: str,
    target_lang_name: str,
    translation_style: str = "standard_dubbing",
) -> Dict[int, str]:
    """
    Dịch một batch câu thoại qua Gemini API với cơ chế tự động tìm model khả dụng,
    hỗ trợ Duration-aware và tối ưu văn phong thuyết minh / review theo translation_style.
    """
    global _CONFIRMED_WORKING_MODEL

    formatted_items = []
    for item in batch_items:
        formatted_items.append({
            "index": item["index"],
            "source_text": item.get("original_text", ""),
            "duration": round(float(item.get("duration", 0.0)), 2),
            "target_speaking_rate": "fast-punchy" if translation_style == "movie_review_spoken_vi" else "natural-medium-fast",
            "preferred_compactness": "concise",
        })

    input_json = json.dumps(formatted_items, ensure_ascii=False, indent=2)
    style_instructions = _build_style_prompt_instructions(translation_style, source_lang_name, target_lang_name)

    prompt = f"""{style_instructions}

Input Transcript Items:
{input_json}
"""


    # Khởi tạo SDK client
    sdk_client = None
    try:
        sdk_client = genai.Client(api_key=api_key)
    except Exception as e:
        logger.warning(f"Không thể khởi tạo genai.Client SDK: {e}")

    # Tự động dò tìm các models khả dụng trên key của user
    candidate_models = _discover_account_models(api_key, sdk_client)

    # Ưu tiên model đã xác nhận hoạt động
    if _CONFIRMED_WORKING_MODEL and _CONFIRMED_WORKING_MODEL in candidate_models:
        candidate_models.remove(_CONFIRMED_WORKING_MODEL)
        candidate_models.insert(0, _CONFIRMED_WORKING_MODEL)

    errors = []

    for model in candidate_models:
        # 1. Thử qua SDK
        if sdk_client:
            try:
                logger.info(f"Đang dịch batch ({len(batch_items)} câu) qua SDK với model '{model}'...")
                response = sdk_client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                    ),
                )
                if response and response.text:
                    translations = _extract_json_translations(response.text)
                    if translations:
                        _CONFIRMED_WORKING_MODEL = model
                        logger.info(f"✓ Dịch thành công qua SDK với model '{model}' ({len(translations)} câu).")
                        return translations
            except Exception as e:
                logger.warning(f"SDK thất bại với model '{model}': {e}")
                errors.append(f"SDK({model}): {e}")

        # 2. Fallback sang Direct REST API
        try:
            logger.info(f"Đang thử Direct REST API với model '{model}'...")
            raw_text = _call_gemini_rest(api_key=api_key, model_name=model, prompt=prompt)
            translations = _extract_json_translations(raw_text)
            if translations:
                _CONFIRMED_WORKING_MODEL = model
                logger.info(f"✓ Dịch thành công qua REST API với model '{model}' ({len(translations)} câu).")
                return translations
        except Exception as e:
            logger.warning(f"REST API thất bại với model '{model}': {e}")
    error_summary = " | ".join(errors[-2:]) if errors else "Không có phản hồi từ Gemini API"
    if any("API_KEY_INVALID" in err or "API key not valid" in err for err in errors):
        raise RuntimeError("Khóa Gemini API không hợp lệ hoặc đã hết hạn (API_KEY_INVALID). Vui lòng bấm 'Thay đổi' tại mục Cấu hình dịch thuật để nhập API Key mới và thử lại.")
    elif any("RESOURCE_EXHAUSTED" in err or "429" in err or "Quota exceeded" in err for err in errors):
        raise RuntimeError("Tài khoản Gemini API đã vượt quá giới hạn lượt gọi (Quota Exceeded / Rate Limit). Vui lòng thử lại sau giây lát hoặc sử dụng API Key khác.")
    raise RuntimeError(f"Dịch thuật thất bại với tất cả model Gemini: {error_summary}")


def recompress_translation_sync(
    api_key: str,
    original_text: str,
    current_translation: str,
    target_duration: float,
    source_lang_name: str = "English",
    target_lang_name: str = "Vietnamese",
) -> str:
    """
    Rút gọn bản dịch tự nhiên (Natural Spoken Compression) khi thời lượng nói thực tế bị tràn:
    Diễn đạt lại cùng một ý nghĩa nhưng cô đọng, ngắn gọn và dễ nói nhanh hơn.
    """
    prompt = f"""You are a voice-over dubbing editor.
The current {target_lang_name} voice-over translation is too long to fit into the audio slot ({target_duration:.2f} seconds).

Original ({source_lang_name}): "{original_text}"
Current translation: "{current_translation}"

TASK:
Rephrase this into a shorter, punchy, highly conversational spoken {target_lang_name} sentence that expresses the exact same core meaning in fewer words, easily spoken in {target_duration:.2f} seconds.

RULES:
1. Return ONLY the new translated sentence string.
2. Do not add quotes, notes, or explanations.
3. Keep vital terms and proper nouns.
"""

    key = _get_api_key(api_key)
    candidate_models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-flash-8b"]
    if _CONFIRMED_WORKING_MODEL:
        candidate_models.insert(0, _CONFIRMED_WORKING_MODEL)

    for model in candidate_models:
        try:
            raw_text = _call_gemini_rest(api_key=key, model_name=model, prompt=prompt)
            compact = raw_text.strip().strip('"').strip("'")
            if compact and len(compact) < len(current_translation):
                logger.info(f"✓ Recompressed translation: '{current_translation}' -> '{compact}'")
                return compact
        except Exception as e:
            logger.warning(f"Recompression failed with {model}: {e}")

    return current_translation


async def translate_transcript_segments(
    transcript_file: Optional[Path] = None,
    output_translated_file: Optional[Path] = None,
    target_language: str = "vi",
    source_language: Optional[str] = "auto",
    api_key: Optional[str] = None,
    batch_size: int = 25,
    translation_style: str = "standard_dubbing",
    *,
    transcript_json_path: Optional[Path] = None,
    output_json_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Dịch toàn bộ transcript JSON theo batch và lưu kết quả bản dịch, hỗ trợ translation_style.
    """
    input_file = transcript_file or transcript_json_path
    if not input_file or not input_file.exists():
        raise FileNotFoundError(f"Không tìm thấy file transcript: {input_file}")

    target_out_file = output_translated_file or output_json_path or input_file
    transcript_file = input_file
    output_translated_file = target_out_file

    # Đọc dữ liệu transcript hiện tại
    async with aiofiles.open(transcript_file, "r", encoding="utf-8") as f:
        content = await f.read()
        data = json.loads(content)

    segments = data.get("speech_chunks") or data.get("segments", [])
    if not segments:
        logger.info("File transcript không chứa đoạn thoại nào cần dịch.")
        empty_res = {
            "segments": [],
            "speech_chunks": [],
            "total_segments": 0,
            "translated_segments": 0,
            "source_language": data.get("detected_language", "en"),
            "target_language": target_language,
            "translation_style": translation_style,
        }
        if output_translated_file:
            output_translated_file.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(output_translated_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(empty_res, indent=2, ensure_ascii=False))
        return empty_res

    key = _get_api_key(api_key)

    detected_lang = data.get("detected_language", "en")
    src_lang = source_language if (source_language and source_language != "auto") else detected_lang
    src_name = LANGUAGE_NAMES.get(src_lang.lower(), f"language '{src_lang}'")
    tgt_name = LANGUAGE_NAMES.get(target_language.lower(), f"language '{target_language}'")

    logger.info(
        f"Bắt đầu dịch {len(segments)} segments từ {src_name} sang {tgt_name} (style='{translation_style}')..."
    )

    # Chia segments thành các batch nhỏ
    batches = [segments[i : i + batch_size] for i in range(0, len(segments), batch_size)]
    all_translations: Dict[int, str] = {}

    loop = asyncio.get_running_loop()

    for idx, batch in enumerate(batches, start=1):
        logger.info(f"Đang xử lý Batch {idx}/{len(batches)} ({len(batch)} câu, style='{translation_style}')...")
        translations = await loop.run_in_executor(
            None,
            _translate_batch_sync,
            key,
            batch,
            src_name,
            tgt_name,
            translation_style,
        )
        all_translations.update(translations)

    # Gán bản dịch vào từng segment
    translated_count = 0
    for seg in segments:
        seg_idx = seg["index"]
        if seg_idx in all_translations:
            seg["translated_text"] = all_translations[seg_idx]
            translated_count += 1
        elif not seg.get("translated_text"):
            seg["translated_text"] = seg.get("original_text", "")

    result_data = {
        "source_language": src_lang,
        "source_language_name": src_name,
        "target_language": target_language,
        "target_language_name": tgt_name,
        "translation_style": translation_style,
        "model_used": _CONFIRMED_WORKING_MODEL or "gemini-2.0-flash",
        "total_segments": len(segments),
        "translated_segments": translated_count,
        "duration": data.get("duration", 0),
        "segments": segments,
        "speech_chunks": segments,
    }

    # Đảm bảo thư mục lưu trữ tồn tại
    output_translated_file.parent.mkdir(parents=True, exist_ok=True)

    # Lưu file translated_transcript.json
    async with aiofiles.open(output_translated_file, "w", encoding="utf-8") as f:
        await f.write(json.dumps(result_data, indent=2, ensure_ascii=False))

    # Đồng bộ cập nhật lại file transcript.json
    async with aiofiles.open(transcript_file, "w", encoding="utf-8") as f:
        await f.write(json.dumps(result_data, indent=2, ensure_ascii=False))

    logger.info(
        f"Hoàn thành dịch thuật ({translated_count}/{len(segments)} câu, style='{translation_style}'). Lưu tại: {output_translated_file.name}"
    )

    return result_data
