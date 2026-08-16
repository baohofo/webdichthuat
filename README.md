# AI Video Translator & AI Dubbing Studio 🎬✨

Ứng dụng web chuyên nghiệp tự động dịch thuật và lồng tiếng video bằng AI: Upload video, trích xuất Dual Audio 48kHz Stereo & 16kHz Mono, nhận diện giọng nói (Faster-Whisper STT với Word Timestamps), dịch thuật ngữ cảnh đa phong cách (Gemini 2.0 / 1.5 Flash), tổng hợp giọng đọc AI (Edge-TTS), cân chỉnh thời lượng nói (Audio Sync), tạo phụ đề kéo thả trực tiếp (Direct Drag & Resize Subtitle Preview), xuất video hoàn chỉnh (ASS Burn-in & FFmpeg Render).

---

## 🌟 Tính Năng Nổi Bật

1. **Pipeline Xử Lý Chuẩn Studio**:
   - **Upload & Batch Processing**: Hỗ trợ tải lên từ 1 đến 5 video cùng lúc (MP4, MKV, MOV, WEBM) với cơ chế hàng đợi xử lý tuần tự và Error Isolation.
   - **Tách giọng & Trích xuất Dual Audio**: Trích xuất đồng thời âm thanh gốc 48000Hz Stereo chất lượng cao và 16000Hz Mono chuẩn STT.
   - **Faster-Whisper STT**: Nhận diện giọng nói siêu tốc với lựa chọn model (`tiny`, `base`, `small`, `medium`, `large-v3`) và Word-level timestamps.
   - **Gemini AI Translation**: Dịch thuật thông minh theo ngữ cảnh với nhiều phong cách (Review phim TikTok kịch tính, lồng tiếng chuẩn mực, thuyết minh vlog tự nhiên).
   - **AI Voice TTS & Voice Presets**: Kho giọng đọc đa dạng (Nam Minh, Hoài My...) với khả năng tùy biến Tốc độ (+15%), Cao độ, Âm lượng giọng đọc và Âm lượng nhạc nền.
   - **Subtitle Direct Manipulation (Kéo Thả & Resize Trực Tiếp)**: Trực tiếp kéo thả vị trí phụ đề trên màn hình video preview, phóng to/thu nhỏ cỡ chữ bằng chuột và xem trước thời gian thực.
   - **ASS Subtitle Burn-in & Export**: Tự động sinh file `.srt`, `.ass` và burn phụ đề cứng sắc nét vào video đầu ra.

2. **Khả Năng Phục Hồi & Bảo Mật Vượt Trội**:
   - **Item-Level Retry & Resume**: Khi gặp lỗi (ví dụ mạng gián đoạn ở TTS chunk 43/120), người dùng có thể bấm "Thử lại từ đoạn lỗi" để tái sử dụng 100% các đoạn đã sinh trước đó.
   - **Lưu trữ API Key an toàn**: Khóa Gemini API được mã hóa bằng thuật ngữ chuẩn công nghiệp AES-GCM 256-bit, lưu an toàn tại máy chủ cục bộ và tự động nạp lại sau khi F5.
   - **Quản lý lịch sử (Job History)**: Xem lại toàn bộ danh sách các tác vụ đã thực hiện, lọc tìm kiếm, tải lại video và phụ đề bất cứ lúc nào.

---

## 🛠️ Yêu Cầu Môi Trường

1. **Python 3.10+** (đã kiểm thử và tương thích hoàn toàn với Python 3.10, 3.11, 3.12, 3.13, 3.14).
2. **FFmpeg & FFprobe**: Đã được cài đặt và có trong biến môi trường `PATH`.

---

## 📦 Hướng Dẫn Cài Đặt

1. **Clone repository**:
```bash
git clone https://github.com/baohofo/webdichthuat.git
cd webdichthuat
```

2. **Cài đặt các thư viện phụ thuộc**:
```bash
pip install -r requirements.txt
```

---

## 🚀 Khởi Chạy Ứng Dụng

Chạy lệnh sau để khởi động máy chủ:

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 5000 --reload
```

Mở trình duyệt web và truy cập:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## ⚙️ Cấu Hình Khóa Gemini API

1. Truy cập [Google AI Studio](https://aistudio.google.com/app/apikey) để lấy Gemini API Key miễn phí.
2. Nhập API Key trực tiếp trên giao diện Studio (mục *Cấu hình dịch thuật*) và bấm **Lưu Key** (Khóa sẽ được mã hóa AES-GCM tự động lưu trên máy).

---

## 📂 Cấu Trúc Thư Mục

```text
├── backend/
│   ├── api/routes.py          # FastAPI Endpoints & Pipeline Orchestration
│   ├── config.py              # Cấu hình đường dẫn, limits, formats
│   ├── main.py                # Server entry point & CORS configuration
│   ├── services/
│   │   ├── audio_extractor.py # Dual audio extraction (48kHz & 16kHz)
│   │   ├── audio_sync_service.py # Time stretching & pause insertion
│   │   ├── render_service.py  # FFmpeg video rendering & ASS burn-in
│   │   ├── stt_service.py     # Faster-Whisper with word timestamps
│   │   ├── subtitle_service.py# SRT & ASS generator with positioning
│   │   ├── translation_service.py # Gemini translation engine
│   │   └── tts_service.py     # Edge-TTS synthesizer with checkpointing
│   └── utils/
│       ├── credential_store.py# AES-GCM encrypted key storage
│       ├── file_utils.py      # Job folder structure & atomic I/O
│       └── job_store.py       # Job state machine & progress tracker
├── frontend/
│   ├── css/style.css          # Rich Studio UI theme & draggable styling
│   ├── js/api.js              # REST API Client wrapper
│   ├── js/app.js              # Interactive UI controller & poller
│   └── index.html             # Studio single-page application
├── requirements.txt           # Python dependencies
└── README.md                  # Project documentation
```
