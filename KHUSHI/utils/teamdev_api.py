"""
KHUSHI — TeamDev YT-API integration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Thin async wrapper around the TeamDev YT-API. The API turns a YouTube URL
into a direct CDN download link in ~1 second, so streaming starts almost
instantly: we hand the CDN URL straight to PyTgCalls without ever touching
disk.

Endpoints (single-shot, no polling):
    GET  {TEAMDEV_API_URL}/api/v1/?url=<yt_url>&fmt=mp3&key=<TEAMDEV_API_KEY>
        → JSON: { status, title, thumbnail, duration, download_url, ... }

Configure via environment variables / Replit secrets:
    TEAMDEV_API_URL   e.g. https://yt.teamdev.sbs
    TEAMDEV_API_KEY   e.g. TD_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
"""

from __future__ import annotations

import asyncio
import os
from typing import Optional, Tuple

import aiohttp

from KHUSHI.logger_setup import LOGGER

_log = LOGGER(__name__)

TEAMDEV_API_URL = (os.getenv("TEAMDEV_API_URL") or "").rstrip("/")
TEAMDEV_API_KEY = os.getenv("TEAMDEV_API_KEY") or ""

# Per-call timeout. The API itself promises ~1-3s; allow extra slack for the
# TLS handshake & first byte from the CDN.
_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=8, connect=4)

# Tiny in-process URL cache so repeated plays of the same vidid skip the
# round-trip entirely. Maps vid -> (download_url, ext).
_url_cache: dict[str, Tuple[str, str]] = {}
_CACHE_MAX = 256


def is_configured() -> bool:
    return bool(TEAMDEV_API_URL and TEAMDEV_API_KEY)


def _yt_url(vid: str) -> str:
    if vid.startswith("http"):
        return vid
    return f"https://www.youtube.com/watch?v={vid}"


def _ext_for_fmt(fmt: str) -> str:
    return "mp3" if fmt == "mp3" else "mp4"


async def _request(session: aiohttp.ClientSession, params: dict) -> Optional[dict]:
    try:
        async with session.get(
            f"{TEAMDEV_API_URL}/api/v1/", params=params
        ) as resp:
            if resp.status != 200:
                _log.debug(
                    f"[TeamDev] non-200 ({resp.status}) for {params.get('url')}"
                )
                return None
            return await resp.json(content_type=None)
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        _log.debug(f"[TeamDev] request error: {e}")
        return None
    except Exception as e:
        _log.debug(f"[TeamDev] unexpected: {e}")
        return None


async def fetch_stream_url(
    vid: str, fmt: str = "mp3"
) -> Optional[Tuple[str, str]]:
    """
    Resolve a YouTube vidid (or full URL) to a direct CDN download URL.

    Returns (download_url, ext) on success, None on any failure.
    The returned URL can be passed straight to PyTgCalls for instant streaming.
    """
    if not is_configured():
        return None

    cached = _url_cache.get(vid)
    if cached:
        return cached

    yt_url = _yt_url(vid)
    params = {"url": yt_url, "fmt": fmt, "key": TEAMDEV_API_KEY}

    async with aiohttp.ClientSession(timeout=_REQUEST_TIMEOUT) as sess:
        data = await _request(sess, params)

    if not data or data.get("status") != "success":
        return None

    dl_url = data.get("download_url")
    if not dl_url:
        return None

    ext = _ext_for_fmt(fmt)
    if len(_url_cache) >= _CACHE_MAX:
        _url_cache.pop(next(iter(_url_cache)), None)
    _url_cache[vid] = (dl_url, ext)
    _log.info(f"[TeamDev] resolved {vid} → CDN url ({ext})")
    return dl_url, ext


async def download_to_file(
    vid: str, out_dir: str, fmt: str = "mp3"
) -> Optional[str]:
    """
    Resolve via TeamDev, then stream the CDN file to local disk and return
    the absolute path. Used as a fallback when caller needs a file (not URL).
    """
    if not is_configured():
        return None

    resolved = await fetch_stream_url(vid, fmt=fmt)
    if not resolved:
        return None

    dl_url, ext = resolved
    out_path = os.path.join(out_dir, f"{vid}.{ext}")

    timeout = aiohttp.ClientTimeout(total=60, connect=10)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.get(dl_url) as resp:
                if resp.status != 200:
                    _log.debug(
                        f"[TeamDev] CDN HTTP {resp.status} for {vid}"
                    )
                    return None
                with open(out_path, "wb") as f:
                    while True:
                        chunk = await resp.content.read(64 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            _log.info(f"[TeamDev] downloaded {vid} → {out_path}")
            return out_path
    except Exception as e:
        _log.debug(f"[TeamDev] download error for {vid}: {e}")

    return None
