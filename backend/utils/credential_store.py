import base64
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from backend.config import DATA_DIR

logger = logging.getLogger("credential_store")

CREDENTIALS_FILE = DATA_DIR / ".credentials.enc"


def _get_encryption_key() -> bytes:
    """
    Sinh khóa AES-256 (32 bytes) dựa trên thông tin máy cục bộ và salt cố định.
    Không hardcode plaintext key, đảm bảo an toàn cục bộ trên máy host.
    """
    machine_id = os.environ.get("COMPUTERNAME", "") + os.environ.get("USERNAME", "") + "AI_DUBBING_STUDIO_SALT_2026"
    return hashlib.sha256(machine_id.encode("utf-8")).digest()


def save_gemini_api_key_sync(api_key: str) -> bool:
    """
    Mã hóa AES-GCM và lưu trữ Gemini API Key vào file bảo mật .credentials.enc.
    """
    if not api_key or not api_key.strip():
        return False

    clean_key = api_key.strip()
    try:
        key = _get_encryption_key()
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        payload = json.dumps({"gemini_api_key": clean_key, "updated_at": os.environ.get("TIME", "")}).encode("utf-8")
        ciphertext = aesgcm.encrypt(nonce, payload, None)

        record = {
            "nonce": base64.b64encode(nonce).decode("utf-8"),
            "data": base64.b64encode(ciphertext).decode("utf-8"),
        }

        CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
            json.dump(record, f)

        logger.info("✓ Gemini credential configured: true (Encrypted storage)")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi mã hóa và lưu trữ API Key: {e}", exc_info=True)
        return False


def get_gemini_api_key_sync() -> Optional[str]:
    """
    Giải mã và đọc Gemini API Key từ file lưu trữ bảo mật.
    """
    if not CREDENTIALS_FILE.exists():
        return None

    try:
        with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
            record = json.load(f)

        nonce = base64.b64decode(record["nonce"])
        ciphertext = base64.b64decode(record["data"])

        key = _get_encryption_key()
        aesgcm = AESGCM(key)
        decrypted = aesgcm.decrypt(nonce, ciphertext, None)
        data = json.loads(decrypted.decode("utf-8"))
        return data.get("gemini_api_key")
    except Exception as e:
        logger.warning(f"Không thể giải mã credential store: {e}")
        return None


def delete_gemini_api_key_sync() -> bool:
    """
    Xóa file lưu trữ khóa API.
    """
    if CREDENTIALS_FILE.exists():
        try:
            CREDENTIALS_FILE.unlink(missing_ok=True)
            logger.info("✓ Đã xóa Gemini API key khỏi credential storage")
            return True
        except Exception as e:
            logger.error(f"Lỗi xóa credential: {e}")
            return False
    return True


def is_gemini_configured_sync() -> bool:
    """
    Kiểm tra xem Gemini API key đã được cấu hình (qua .env hoặc qua credential store).
    """
    from backend.config import GEMINI_API_KEY
    if GEMINI_API_KEY and GEMINI_API_KEY.strip():
        return True
    key = get_gemini_api_key_sync()
    return bool(key and key.strip())
