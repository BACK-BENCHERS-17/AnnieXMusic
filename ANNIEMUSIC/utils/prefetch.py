"""
Pre-fetch next queue tracks in background while current song plays.
Eliminates download wait when queue moves to next song.
"""

import asyncio
import logging
from typing import Optional

from ANNIEMUSIC.misc import db
from ANNIEMUSIC.utils.downloader import download_audio_concurrent, file_exists, extract_video_id

_log = logging.getLogger(__name__)

_prefetch_tasks: dict[int, asyncio.Task] = {}


async def _prefetch_worker(chat_id: int, vidid: str, link: str) -> None:
    try:
        cached = file_exists(vidid)
        if cached:
            _log.info(f"[PREFETCH] Already cached: {vidid}")
            return
        _log.info(f"[PREFETCH] Starting background download for {vidid} (chat={chat_id})")
        path = await download_audio_concurrent(link)
        if path:
            _log.info(f"[PREFETCH] Done: {vidid} → {path}")
        else:
            _log.warning(f"[PREFETCH] Failed for {vidid}")
    except asyncio.CancelledError:
        pass
    except Exception as e:
        _log.debug(f"[PREFETCH] Error for {vidid}: {e}")
    finally:
        _prefetch_tasks.pop(chat_id, None)


def trigger_prefetch(chat_id: int) -> None:
    """
    Check queue index 1 (next song after current).
    If it's a YouTube vid_ item not yet cached, start downloading in background.
    Called right after a song starts playing.
    """
    try:
        queue = db.get(chat_id)
        if not queue or len(queue) < 2:
            return

        next_item = queue[1]
        queued_file: str = next_item.get("file", "")
        vidid: str = next_item.get("vidid", "")
        streamtype: str = next_item.get("streamtype", "")

        if "vid_" not in queued_file:
            return
        if not vidid or streamtype not in ("audio", "video"):
            return

        if file_exists(vidid):
            _log.info(f"[PREFETCH] Next track already cached: {vidid}")
            return

        existing = _prefetch_tasks.get(chat_id)
        if existing and not existing.done():
            return

        link = f"https://www.youtube.com/watch?v={vidid}"
        task = asyncio.create_task(_prefetch_worker(chat_id, vidid, link))
        _prefetch_tasks[chat_id] = task
        _log.info(f"[PREFETCH] Queued prefetch for vidid={vidid} chat={chat_id}")
    except Exception as e:
        _log.debug(f"[PREFETCH] trigger error: {e}")


def cancel_prefetch(chat_id: int) -> None:
    """Cancel any running prefetch for a chat (on skip/stop)."""
    task = _prefetch_tasks.pop(chat_id, None)
    if task and not task.done():
        task.cancel()
