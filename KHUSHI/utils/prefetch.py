"""
Pre-fetch next queue tracks in background while current song plays.

Strategy:
  1. Use fast_get_stream() which:
     - checks local file (instant)
     - races webserver URL cache vs SmartYTDL extraction (parallel)
     - kicks off background local file download after URL is found
  2. After prefetch, the resolved URL/path is INJECTED BACK into the queue entry.
     This means when the song's turn comes, the play handler finds a real path
     (not "vid_...") and skips the YouTube.download() call entirely → 0ms delay.
  3. Pre-fetch the next TWO songs in queue (not just one).
"""

import asyncio
import logging

from KHUSHI.misc import db
from KHUSHI.utils.downloader import file_exists, fast_get_stream

_log = logging.getLogger(__name__)

_prefetch_tasks: dict[str, asyncio.Task] = {}


def _inject_resolved_url(chat_id: int, vidid: str, resolved: str) -> None:
    """
    After prefetch, update the queue entry's 'file' field from 'vid_<vidid>'
    to the actual resolved path or CDN URL. This lets the play handler skip
    the YouTube.download() call entirely → near-zero queue transition delay.
    """
    try:
        queue = db.get(chat_id)
        if not queue:
            return
        for item in queue:
            if item.get("vidid") == vidid and item.get("file", "").startswith("vid_"):
                item["file"] = resolved
                _log.info(
                    f"[PREFETCH] Injected into queue: {vidid} → "
                    f"{'local' if not resolved.startswith('http') else 'cdn'}"
                )
                return
    except Exception as e:
        _log.debug(f"[PREFETCH] Inject failed for {vidid}: {e}")


async def _prefetch_worker(chat_id: int, vidid: str) -> None:
    try:
        if file_exists(vidid):
            _log.info(f"[PREFETCH] Already cached locally: {vidid}")
            # Still inject the local path so the play handler skips download()
            local = file_exists(vidid)
            if local:
                _inject_resolved_url(chat_id, vidid, local)
            return

        _log.info(f"[PREFETCH] Pre-warming CDN URL + bg download for {vidid}")
        result = await fast_get_stream(vidid)
        if result:
            _inject_resolved_url(chat_id, vidid, result)
            _log.info(
                f"[PREFETCH] Ready: {vidid} → "
                f"{'local' if not result.startswith('http') else 'cdn'}"
            )
        else:
            _log.warning(f"[PREFETCH] Failed for {vidid}")
    except asyncio.CancelledError:
        pass
    except Exception as e:
        _log.debug(f"[PREFETCH] Error for {vidid}: {e}")
    finally:
        _prefetch_tasks.pop(vidid, None)


def trigger_prefetch(chat_id: int) -> None:
    """
    Pre-fetch the next 1-2 YouTube songs in queue while the current song plays.
    Uses fast_get_stream which warms both the webserver URL cache and local file.
    After resolution, injects the result back into the queue entry so the play
    handler can start the next song instantly (no YouTube.download() call).
    Called right after a song starts playing.
    """
    try:
        queue = db.get(chat_id)
        if not queue or len(queue) < 2:
            return

        for next_item in queue[1:3]:
            queued_file: str = next_item.get("file", "")
            vidid: str = next_item.get("vidid", "")
            streamtype: str = next_item.get("streamtype", "")

            if "vid_" not in queued_file:
                continue
            if not vidid or streamtype not in ("audio", "video"):
                continue

            # Already resolved by a previous prefetch cycle
            if not next_item.get("file", "").startswith("vid_"):
                _log.info(f"[PREFETCH] Already resolved in queue: {vidid}")
                continue

            existing = _prefetch_tasks.get(vidid)
            if existing and not existing.done():
                _log.info(f"[PREFETCH] Already in flight: {vidid}")
                continue

            task = asyncio.create_task(_prefetch_worker(chat_id, vidid))
            _prefetch_tasks[vidid] = task
            _log.info(f"[PREFETCH] Triggered for vidid={vidid} chat={chat_id}")

    except Exception as e:
        _log.debug(f"[PREFETCH] trigger error: {e}")


def cancel_prefetch(chat_id: int) -> None:
    """Cancel prefetch tasks for songs in this chat's queue (on skip/stop)."""
    try:
        queue = db.get(chat_id) or []
        for item in queue[1:3]:
            vidid = item.get("vidid", "")
            if vidid and vidid in _prefetch_tasks:
                task = _prefetch_tasks.pop(vidid)
                if not task.done():
                    task.cancel()
    except Exception:
        pass
