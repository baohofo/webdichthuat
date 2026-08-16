import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.routes import router as api_router
from backend.config import FRONTEND_DIR, HOST, PORT
from backend.utils.ffmpeg_utils import is_ffmpeg_available

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("==================================================")
    logger.info("   AI VIDEO TRANSLATOR & DUBBING SERVER STARTING   ")
    logger.info("==================================================")
    if is_ffmpeg_available():
        logger.info("✓ FFmpeg & FFprobe: Đã phát hiện và sẵn sàng hoạt động.")
    else:
        logger.warning("✗ FFmpeg: Chưa được cài đặt hoặc không tìm thấy trong PATH!")
    logger.info(f"Frontend running at: http://{HOST}:{PORT}")
    logger.info("==================================================")
    yield
    logger.info("Server shutting down...")


app = FastAPI(
    title="AI Video Translator & Dubbing API",
    version="1.0.0",
    description="Hệ thống dịch thuật và lồng tiếng video bằng AI tự động",
    lifespan=lifespan,
)

# Cấu hình CORS để hỗ trợ gọi API từ mọi nguồn
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các API routes
app.include_router(api_router)

# Mount thư mục Frontend tĩnh
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=HOST,
        port=PORT,
        reload=True,
        reload_dirs=["backend"],
        reload_excludes=["data", "data/*", "scratch", "scratch/*", "frontend", "frontend/*"],
    )
