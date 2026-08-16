import re
import uuid
from pathlib import Path
from typing import Dict, Optional
from backend.config import JOBS_DIR, ALLOWED_VIDEO_EXTENSIONS


def sanitize_filename(filename: str) -> str:
    """
    Làm sạch tên file để tránh tấn công Path Traversal và ký tự đặc biệt gây lỗi hệ điều hành.
    Hỗ trợ đầy đủ ký tự Unicode (tiếng Việt, tiếng Nhật, tiếng Trung...).
    """
    # Lấy chỉ tên file gốc (bỏ mọi đường dẫn phía trước)
    clean_name = Path(filename).name
    # Thay thế các ký tự cấm của hệ điều hành bằng dấu gạch dưới: \ / : * ? " < > |
    clean_name = re.sub(r'[\r\n\t\\/:*?"<>|\x00-\x1f]', '_', clean_name)
    # Loại bỏ dấu chấm hoặc khoảng trắng ở đầu/cuối
    clean_name = clean_name.strip('. ')
    # Rút ngắn nếu tên quá dài
    if len(clean_name) > 120:
        stem = Path(clean_name).stem[:100]
        ext = Path(clean_name).suffix
        clean_name = f"{stem}{ext}"
    return clean_name or "video.mp4"


def is_allowed_video_file(filename: str) -> bool:
    """
    Kiểm tra đuôi file có thuộc danh sách video cho phép không (.mp4, .mov, .mkv, .webm)
    """
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_VIDEO_EXTENSIONS


def create_job_directory(job_id: Optional[str] = None) -> Dict[str, Path]:
    """
    Tạo thư mục làm việc riêng biệt cho từng Job xử lý video.
    Cấu trúc:
    data/jobs/<job_id>/
      ├── input/
      ├── audio/
      ├── transcript/
      ├── tts/
      ├── subtitles/
      └── output/
    """
    if not job_id:
        job_id = str(uuid.uuid4())

    job_dir = JOBS_DIR / job_id
    paths = {
        "job_id": job_id,
        "job_dir": job_dir,
        "input_dir": job_dir / "input",
        "audio_dir": job_dir / "audio",
        "transcript_dir": job_dir / "transcript",
        "tts_dir": job_dir / "tts",
        "subtitles_dir": job_dir / "subtitles",
        "output_dir": job_dir / "output",
    }

    for key, path in paths.items():
        if key != "job_id":
            path.mkdir(parents=True, exist_ok=True)

    return paths


def get_job_paths(job_id: str) -> Optional[Dict[str, Path]]:
    """
    Lấy thông tin đường dẫn các thư mục của một Job đã tồn tại.
    """
    # Sanitize job_id để tránh path traversal
    safe_job_id = re.sub(r'[^a-zA-Z0-9_-]', '', job_id)
    job_dir = JOBS_DIR / safe_job_id
    if not job_dir.exists() or not job_dir.is_dir():
        return None

    return {
        "job_id": safe_job_id,
        "job_dir": job_dir,
        "input_dir": job_dir / "input",
        "audio_dir": job_dir / "audio",
        "transcript_dir": job_dir / "transcript",
        "tts_dir": job_dir / "tts",
        "subtitles_dir": job_dir / "subtitles",
        "output_dir": job_dir / "output",
    }


def format_file_size(size_in_bytes: int) -> str:
    """
    Định dạng dung lượng file theo chuẩn người dùng dễ đọc (KB, MB, GB)
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} TB"
