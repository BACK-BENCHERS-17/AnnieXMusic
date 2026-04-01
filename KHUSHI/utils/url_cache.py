"""
Persistent YouTube CDN URL cache backed by MongoDB.

Every time a CDN URL is successfully extracted for a video, it is saved here.
On the NEXT request — by ANY user, even after a bot restart — the URL is served
from MongoDB in < 50 ms instead of spending 5-15 seconds re-extracting it.

TTL is derived from YouTube's own `expire` query parameter (typically 6 hours).
MongoDB automatically deletes documents after they expire (TTL index).
"""

import logging
import time
from typing import Optional, Tuple
from urllib.parse import parse_qs, urlparse

_log = logging.getLogger(__name__)

# Populated lazily after the event loop + MongoDB client are ready.
_collection = None
_index_ensured = False


def _get_col():
    global _collection
    if _collection is not None:
        return _collection
    try:
        from KHUSHI.core.mongo import mongodb
        _collection = mongodb["yt_url_cache"]
    except Exception as e:
        _log.warning(f"[URLCache] MongoDB unavailable: {e}")
    return _collection


def _parse_expiry(url: str) -> int:
    """Return the Unix timestamp when this YouTube CDN URL expires (minus 5 min safety)."""
    try:
        qs = parse_qs(urlparse(url).query)
        exp = qs.get("expire", [None])[0]
        if exp:
            return int(exp) - 300   # 5-minute safety margin
    except Exception:
        pass
    return int(time.time()) + 3600  # fallback: 1 hour


async def _ensure_index() -> None:
    global _index_ensured
    if _index_ensured:
        return
    col = _get_col()
    if col is None:
        return
    try:
        await col.create_index("expires_at", expireAfterSeconds=0)
        _index_ensured = True
    except Exception as e:
        _log.debug(f"[URLCache] Index creation skipped: {e}")


async def get_url(vid: str) -> Optional[Tuple[str, str]]:
    """
    Return (cdn_url, ext) from MongoDB if still valid, else None.
    Typical latency: 5-30 ms.
    """
    col = _get_col()
    if col is None:
        return None
    try:
        doc = await col.find_one({"_id": vid})
        if not doc:
            return None
        # Double-check client-side in case Mongo TTL hasn't fired yet
        if doc.get("expires_at", 0) < time.time():
            return None
        url = doc.get("url", "")
        ext = doc.get("ext", "m4a")
        if url:
            _log.info(f"[URLCache] MongoDB hit for {vid}")
            return url, ext
    except Exception as e:
        _log.debug(f"[URLCache] get_url failed for {vid}: {e}")
    return None


async def put_url(vid: str, url: str, ext: str = "m4a") -> None:
    """
    Save (cdn_url, ext) to MongoDB. Fire-and-forget — caller should not await if latency matters.
    """
    col = _get_col()
    if col is None:
        return
    await _ensure_index()
    expires_at = _parse_expiry(url)
    try:
        await col.update_one(
            {"_id": vid},
            {"$set": {
                "url": url,
                "ext": ext,
                "expires_at": expires_at,
                "saved_at": int(time.time()),
            }},
            upsert=True,
        )
        _log.debug(f"[URLCache] Saved to MongoDB: {vid} (ext={ext})")
    except Exception as e:
        _log.debug(f"[URLCache] put_url failed for {vid}: {e}")
