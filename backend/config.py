import os
from pathlib import Path
from dotenv import load_dotenv

# Tự động nạp file .env nếu có
load_dotenv()

# Đường dẫn gốc của dự án (dichthuat/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Thư mục dữ liệu & Jobs
DATA_DIR = BASE_DIR / "data"
JOBS_DIR = DATA_DIR / "jobs"

# Thư mục Frontend
FRONTEND_DIR = BASE_DIR / "frontend"

# Đảm bảo các thư mục cần thiết luôn tồn tại
JOBS_DIR.mkdir(parents=True, exist_ok=True)

# Các định dạng video được hỗ trợ
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}

# Giới hạn kích thước file upload (mặc định 500 MB)
MAX_UPLOAD_SIZE_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", 500 * 1024 * 1024))

# Cấu hình Server
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", 5000))

# Cấu hình AI & TTS
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
WHISPER_DEFAULT_MODEL = os.getenv("WHISPER_DEFAULT_MODEL", "small")

# ==========================================
# CẤU HÌNH AUDIO CHUẨN XUẤT BẢN (48 kHz Stereo)
# ==========================================
WHISPER_AUDIO_SAMPLE_RATE = 16000     # 16 kHz Mono PCM CHỈ dùng cho Faster-Whisper STT
WHISPER_AUDIO_CHANNELS = 1

FINAL_AUDIO_SAMPLE_RATE = 48000       # 48 kHz Stereo chuẩn chất lượng cao cho Video Render
FINAL_AUDIO_CHANNELS = 2
FINAL_AUDIO_BITRATE = "192k"
FINAL_AUDIO_CODEC = "aac"

# ==========================================
# CẤU HÌNH SPEECH CHUNKING CHO TTS
# ==========================================
PREFERRED_CHUNK_MIN_DURATION = 2.0    # Thời lượng chunk ưu tiên tối thiểu (giây)
PREFERRED_CHUNK_MAX_DURATION = 6.0    # Thời lượng chunk ưu tiên tối đa (giây)
SOFT_MAX_CHUNK_DURATION = 7.0         # Ngưỡng mềm tìm điểm cắt tự nhiên (giây)
HARD_MAX_CHUNK_DURATION = 9.0         # Giới hạn cứng tuyệt đối cho 1 SpeechChunk (giây)
CHUNK_MERGE_MAX_GAP = 0.6             # Khoảng nghỉ tối đa giữa các segment để xem xét gộp (giây)
MIN_CHUNK_WORDS_FOR_MERGE = 4         # Ngưỡng số từ để xem xét câu độc lập

# ==========================================
# CẤU HÌNH DETERMINISTIC NATURAL PAUSE MODEL (TIÊU CHUẨN)
# ==========================================
PAUSE_COMMA = 0.15                    # Dấu phẩy, gạch ngang (giây)
PAUSE_COLON_SEMICOLON = 0.22          # Dấu hai chấm, chấm phẩy (giây)
PAUSE_SENTENCE_END = 0.32             # Dấu chấm, chấm than, hỏi chấm (giây)
PAUSE_PARAGRAPH_TRANSITION = 0.60     # Chuyển cảnh / khoảng nghỉ lớn (giây)

# ==========================================
# CẤU HÌNH PAUSE PROFILE — MOVIE REVIEW / TIKTOK
# ==========================================
MOVIE_REVIEW_PAUSE_COMMA = 0.10               # Dấu phẩy (0.08–0.15s)
MOVIE_REVIEW_PAUSE_COLON_SEMICOLON = 0.16     # Hai chấm, chấm phẩy (0.12–0.22s)
MOVIE_REVIEW_PAUSE_SENTENCE_END = 0.25        # Kết thúc câu (0.20–0.35s)
MOVIE_REVIEW_PAUSE_TRANSITION = 0.38          # Chuyển tình tiết (0.30–0.55s)
MOVIE_REVIEW_PAUSE_DRAMATIC = 0.50            # Chuyển cảnh kịch tính (0.45–0.75s)

PAUSE_PROFILES = {
    "standard": {
        "comma": PAUSE_COMMA,
        "colon_semicolon": PAUSE_COLON_SEMICOLON,
        "sentence_end": PAUSE_SENTENCE_END,
        "transition": PAUSE_PARAGRAPH_TRANSITION,
    },
    "movie_review": {
        "comma": MOVIE_REVIEW_PAUSE_COMMA,
        "colon_semicolon": MOVIE_REVIEW_PAUSE_COLON_SEMICOLON,
        "sentence_end": MOVIE_REVIEW_PAUSE_SENTENCE_END,
        "transition": MOVIE_REVIEW_PAUSE_TRANSITION,
        "dramatic": MOVIE_REVIEW_PAUSE_DRAMATIC,
    },
}

# ==========================================
# CẤU HÌNH PHÂN ĐOẠN PHỤ ĐỀ (SUBTITLE SEGMENTATION)
# ==========================================
SUBTITLE_MAX_LINES = 2
SUBTITLE_MAX_CHARS_PER_LINE = 42
SUBTITLE_TARGET_CPS = 18.0            # Tốc độ đọc mục tiêu (ký tự / giây)
SUBTITLE_MAX_CPS = 22.0               # Ngưỡng tối đa cảnh báo CPS cao
SUBTITLE_WARN_UNDER_DURATION = 0.8    # Cảnh báo phụ đề dưới 0.8s
SUBTITLE_WARN_OVER_DURATION = 6.0     # Cảnh báo phụ đề vượt 6.0s
SUBTITLE_GAP_WARNING_THRESHOLD = 4.0  # Ngưỡng cảnh báo khoảng trống không phụ đề (>4s)

# ==========================================
# CẤU HÌNH ĐỒNG BỘ GIỌNG NÓI AI & ATEMPO POLICY
# ==========================================
ATEMPO_NORMAL_MAX = 1.15              # <= 1.15x: Bình thường (Optimal)
ATEMPO_ACCEPTABLE_MAX = 1.25          # 1.15x - 1.25x: Chấp nhận khi cần
ATEMPO_HARD_MAX = 1.40                # 1.25x - 1.40x: Cảnh báo / Emergency only
TTS_PREFERRED_MAX_SPEEDUP = 1.15
TTS_HARD_MAX_SPEEDUP = 1.40
TTS_DEFAULT_BREATHING_PAUSE = 0.32

