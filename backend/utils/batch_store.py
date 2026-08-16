import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import DATA_DIR
from backend.utils.job_store import load_job_info

logger = logging.getLogger("batch_store")

BATCHES_DIR = DATA_DIR / "batches"
BATCHES_DIR.mkdir(parents=True, exist_ok=True)

_BATCH_LOCKS: Dict[str, asyncio.Lock] = {}


def _get_batch_lock(batch_id: str) -> asyncio.Lock:
    if batch_id not in _BATCH_LOCKS:
        _BATCH_LOCKS[batch_id] = asyncio.Lock()
    return _BATCH_LOCKS[batch_id]


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_batch_dir(batch_id: str) -> Path:
    b_dir = BATCHES_DIR / batch_id
    b_dir.mkdir(parents=True, exist_ok=True)
    return b_dir


def save_batch_info_atomic_sync(batch_id: str, batch_info: Dict[str, Any]) -> None:
    """
    Ghi batch_info.json theo cơ chế Atomic Write có retry cho Windows.
    """
    b_dir = get_batch_dir(batch_id)
    batch_file = b_dir / "batch_info.json"
    temp_file = b_dir / f"batch_info_{int(time.time()*1000)}.tmp"

    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(batch_info, f, indent=2, ensure_ascii=False)

        for attempt in range(5):
            try:
                os.replace(str(temp_file), str(batch_file))
                break
            except (PermissionError, OSError):
                if attempt == 4:
                    with open(batch_file, "w", encoding="utf-8") as f:
                        json.dump(batch_info, f, indent=2, ensure_ascii=False)
                else:
                    time.sleep(0.01 * (attempt + 1))
    except Exception as e:
        logger.error(f"Lỗi atomic write batch_info cho {batch_id}: {e}", exc_info=True)
    finally:
        if temp_file.exists():
            try:
                temp_file.unlink(missing_ok=True)
            except Exception:
                pass


async def save_batch_info_atomic(batch_id: str, batch_info: Dict[str, Any]) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, save_batch_info_atomic_sync, batch_id, batch_info)


def load_batch_info_sync(batch_id: str) -> Optional[Dict[str, Any]]:
    batch_file = get_batch_dir(batch_id) / "batch_info.json"
    if not batch_file.exists():
        return None

    for attempt in range(3):
        try:
            with open(batch_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, PermissionError):
            time.sleep(0.02 * (attempt + 1))
    return None


async def load_batch_info(batch_id: str) -> Optional[Dict[str, Any]]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, load_batch_info_sync, batch_id)


async def create_batch(job_ids: List[str]) -> Dict[str, Any]:
    """
    Tạo cấu trúc Batch quản lý danh sách Job ID (1–5 videos).
    """
    batch_id = str(uuid.uuid4())
    batch_info = {
        "batch_id": batch_id,
        "status": "created",
        "created_at": _iso_now(),
        "total_jobs": len(job_ids),
        "current_job_id": job_ids[0] if job_ids else None,
        "current_job_index": 0 if job_ids else -1,
        "jobs": job_ids,
        "progress": 0.0,
        "error": None,
    }
    await save_batch_info_atomic(batch_id, batch_info)
    return batch_info


async def calculate_batch_progress(batch_info: Dict[str, Any]) -> float:
    """
    Tính tiến độ tổng hợp thật của Batch dựa trên tiến độ thật của từng Job trong batch.
    """
    job_ids = batch_info.get("jobs", [])
    if not job_ids:
        return 0.0

    total_pct = 0.0
    for j_id in job_ids:
        j_info = await load_job_info(j_id)
        if j_info:
            total_pct += float(j_info.get("progress", 0.0))

    return round(total_pct / len(job_ids), 1)


async def update_batch_state(
    batch_id: str,
    status: Optional[str] = None,
    current_job_id: Optional[str] = None,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    lock = _get_batch_lock(batch_id)
    async with lock:
        batch_info = await load_batch_info(batch_id)
        if not batch_info:
            return {}

        if status:
            batch_info["status"] = status
        if current_job_id is not None:
            batch_info["current_job_id"] = current_job_id
            job_ids = batch_info.get("jobs", [])
            if current_job_id in job_ids:
                batch_info["current_job_index"] = job_ids.index(current_job_id)
        if error:
            batch_info["error"] = error

        batch_info["progress"] = await calculate_batch_progress(batch_info)
        await save_batch_info_atomic(batch_id, batch_info)
        return batch_info
