import asyncio
import logging
import re
from typing import Any, Awaitable, Callable, Optional, Tuple

logger = logging.getLogger("retry_utils")

# Danh sách chuỗi nhận diện lỗi Fatal (Không bao giờ thử lại tự động)
FATAL_ERROR_PATTERNS = [
    "API_KEY_INVALID",
    "API key not valid",
    "INVALID_GEMINI_API_KEY",
    "API_KEY_EXPIRED",
    "UNAUTHENTICATED",
    "PERMISSION_DENIED",
    "INVALID_ARGUMENT",
    "INVALID_WHISPER_MODEL",
    "UNSUPPORTED_MODEL",
    "INPUT_FILE_MISSING",
    "NO_AUDIO_STREAM",
    "AUTHENTICATION_FAILED",
    "FILE_TOO_LARGE",
]

# Danh sách chuỗi nhận diện lỗi Recoverable (Được phép tự động thử lại)
RECOVERABLE_ERROR_PATTERNS = [
    "RESOURCE_EXHAUSTED",
    "RATE_LIMIT",
    "429",
    "HTTP 429",
    "500",
    "502",
    "503",
    "504",
    "HTTP 500",
    "HTTP 502",
    "HTTP 503",
    "HTTP 504",
    "NETWORK_TIMEOUT",
    "CONNECTION_RESET",
    "TEMPORARY_PROVIDER_ERROR",
    "EDGE_TTS_TEMPORARY_FAILURE",
    "TIMED OUT",
    "TIMEOUT",
    "CONNECTERROR",
    "WSS",
    "WEBSOCKET",
    "PROCESS_GLITCH",
    "BROKEN PIPE",
    "CONNECTION REFUSED",
    "CONNECTION RESET",
    "SERVER DISCONNECTED",
]


def is_fatal_api_key_error(exc: Any) -> bool:
    """
    Kiểm tra chính xác xem lỗi có phải do Gemini API Key không hợp lệ hoặc đã hết hạn.
    """
    err_str = str(exc).upper()
    return any(p.upper() in err_str for p in ["API_KEY_INVALID", "API KEY NOT VALID", "INVALID_GEMINI_API_KEY", "UNAUTHENTICATED"])


def is_recoverable_error(exc: Any) -> bool:
    """
    Phân loại lỗi:
    - Trả về False nếu lỗi thuộc nhóm FATAL_ERROR_PATTERNS (API Key sai, File thiếu, Model không hỗ trợ).
    - Trả về True nếu lỗi thuộc nhóm mạng, timeout, rate limit (429), lỗi server (5xx), hoặc EdgeTTS WSS.
    """
    if is_fatal_api_key_error(exc):
        return False

    err_str = str(exc).upper()

    # 1. Kiểm tra loại trừ lỗi Fatal rõ ràng
    for pattern in FATAL_ERROR_PATTERNS:
        if pattern.upper() in err_str:
            return False

    # 2. Kiểm tra các Exception types mạng / timeout chuẩn
    exc_type_name = type(exc).__name__.upper() if isinstance(exc, Exception) else ""
    if any(t in exc_type_name for t in ["TIMEOUT", "CONNECT", "NETWORK", "RESET", "SOCKET", "BROKENPIPE", "OSERROR"]):
        return True

    # 3. Kiểm tra các pattern có thể phục hồi
    for pattern in RECOVERABLE_ERROR_PATTERNS:
        if pattern.upper() in err_str:
            return True

    # Mặc định: Nếu là Exception thông thường không thuộc blacklist fatal thì cho phép thử lại có giới hạn
    if isinstance(exc, (RuntimeError, OSError, ConnectionError, IOError)):
        return True

    return False


def get_retry_after_delay(exc: Any, default_delay: float = 2.0) -> float:
    """
    Trích xuất thời gian chờ từ phản hồi HTTP 429 Retry-After nếu có,
    hoặc trả về default_delay (tối đa 10s để không làm nghẽn pipeline).
    """
    err_str = str(exc)
    # Tìm kiếm pattern Retry-After: \d+ hoặc retry after \d+
    match = re.search(r"(?:retry-after|retry after|retry in)[:\s]+(\d+(?:\.\d+)?)", err_str, re.IGNORECASE)
    if match:
        try:
            val = float(match.group(1))
            return max(1.0, min(10.0, val))
        except (ValueError, TypeError):
            pass
    return max(1.0, min(10.0, default_delay))


async def execute_with_auto_retry(
    func: Callable[..., Awaitable[Any]],
    *args: Any,
    max_attempts: int = 3,
    initial_backoff: float = 1.0,
    backoff_factor: float = 2.0,
    max_backoff: float = 6.0,
    stage_name: str = "stage",
    on_retry_callback: Optional[Callable[[int, int, Exception, float], Awaitable[None]]] = None,
    on_recovered_callback: Optional[Callable[[int], Awaitable[None]]] = None,
    **kwargs: Any,
) -> Any:
    """
    Generic Async Auto-Retry Runner dành cho Stage-Level (STT, Audio Sync, Subtitle, Render, Extract Audio).
    - Tối đa max_attempts lượt thử (Mặc định: 3 attempts = 1 lần chính + 2 lần tự thử lại).
    - Bounded Exponential Backoff: 1s -> 2s -> 4s (tối đa max_backoff).
    - Nếu gặp lỗi Fatal (như API_KEY_INVALID, INVALID_CONFIG, FILE_MISSING): DỪNG NGAY LẬP TỨC ở attempt 1.
    - Cung cấp callback realtime cập nhật thông điệp lên UI.
    """
    last_error: Optional[Exception] = None
    current_backoff = initial_backoff

    for attempt in range(1, max_attempts + 1):
        try:
            result = await func(*args, **kwargs)
            if attempt > 1 and on_recovered_callback:
                try:
                    await on_recovered_callback(attempt)
                except Exception as cb_err:
                    logger.warning(f"Lỗi on_recovered_callback trong stage {stage_name}: {cb_err}")
            return result

        except Exception as e:
            last_error = e

            # Nếu là lỗi Fatal: Dừng ngay lập tức, KHÔNG thử lại
            if not is_recoverable_error(e):
                logger.warning(
                    f"[{stage_name.upper()}] Gặp lỗi Fatal / Không thể tự phục hồi (Attempt {attempt}/{max_attempts}): {e}. Dừng ngay lập tức."
                )
                raise e

            if attempt < max_attempts:
                # Tính toán thời gian chờ backoff
                wait_time = get_retry_after_delay(e, current_backoff)
                logger.warning(
                    f"[{stage_name.upper()}] Lỗi tạm thời (Attempt {attempt}/{max_attempts}): {e}. Tự động thử lại lần {attempt}/{max_attempts - 1} sau {wait_time:.1f}s..."
                )

                if on_retry_callback:
                    try:
                        await on_retry_callback(attempt, max_attempts, e, wait_time)
                    except Exception as cb_err:
                        logger.warning(f"Lỗi on_retry_callback trong stage {stage_name}: {cb_err}")

                await asyncio.sleep(wait_time)
                current_backoff = min(max_backoff, current_backoff * backoff_factor)
            else:
                logger.error(
                    f"[{stage_name.upper()}] Đã hết {max_attempts} lượt thử lại tự động mà vẫn thất bại: {e}"
                )

    raise RuntimeError(
        f"{stage_name.upper()}_AUTO_RETRY_EXHAUSTED: Thất bại sau {max_attempts} lần thử tự động: {last_error}"
    ) from last_error
