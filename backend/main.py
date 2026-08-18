import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.routes import router as api_router
from backend.config import FRONTEND_DIR, HOST, PORT, RUNTIME_INSTANCE_ID
from backend.utils.ffmpeg_utils import is_ffmpeg_available
from backend.utils.job_store import recover_stale_running_jobs

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
    logger.info(f"   RUNTIME_INSTANCE_ID: {RUNTIME_INSTANCE_ID}")
    logger.info("==================================================")
    if is_ffmpeg_available():
        logger.info("✓ FFmpeg & FFprobe: Đã phát hiện và sẵn sàng hoạt động.")
    else:
        logger.warning("✗ FFmpeg: Chưa được cài đặt hoặc không tìm thấy trong PATH!")

    # Khởi động Watchdog thu hồi các tác vụ zombie do server khởi động lại (Invariant 4)
    try:
        recovered = await recover_stale_running_jobs()
        if recovered:
            logger.info(f"[WATCHDOG] Đã phát hiện và phục hồi {len(recovered)} zombie jobs: {', '.join(recovered)}")
        else:
            logger.info("[WATCHDOG] Không có zombie job nào cần thu hồi.")
    except Exception as e:
        logger.error(f"[WATCHDOG] Lỗi khi thu hồi zombie jobs lúc khởi động: {e}", exc_info=True)

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


@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.endswith((".js", ".css", ".html")) or path == "/" or "/js/" in path or "/css/" in path:
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


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
