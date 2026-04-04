"""
KHUSHI — Built-in aiohttp web server for the web player.
Serves KHUSHI/web/index.html and JSON API endpoints on the configured host:port.
"""

import asyncio
import logging
import os
import time
from typing import Optional

from aiohttp import web

_log = logging.getLogger(__name__)

_WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
_INDEX   = os.path.join(_WEB_DIR, "index.html")

# ── simple in-process cache for trending results (TTL = 30 min) ──────────────
_trending_cache: list = []
_trending_ts: float = 0.0
_TRENDING_TTL: float = 1800.0

# tracks in-progress audio downloads so we don't double-download
_audio_locks: dict = {}


# ── helpers ───────────────────────────────────────────────────────────────────

def _download_dir() -> str:
    try:
        from KHUSHI.core.dir import DOWNLOAD_DIR
        return DOWNLOAD_DIR
    except Exception:
        return os.path.join(os.getcwd(), "downloads")


def _find_audio(vid: str) -> Optional[str]:
    """Return a local audio file path if the video id was already downloaded."""
    d = _download_dir()
    for ext in ("m4a", "mp3", "webm", "opus"):
        p = os.path.join(d, f"{vid}.{ext}")
        if os.path.isfile(p):
            return p
    return None


async def _fetch_search(query: str, limit: int = 10) -> list:
    """Search YouTube via the bot's existing search utilities."""
    try:
        from KHUSHI.utils.yt_api import yt_api_search
        results = await yt_api_search(query, max_results=limit)
        if results:
            return results
    except Exception:
        pass
    try:
        from KHUSHI.utils.fast_stream import search_youtube
        raw = await search_youtube(query, limit=limit)
        out = []
        for r in raw:
            vid_id = r.get("vid_id") or r.get("id", "")
            if not vid_id:
                continue
            out.append({
                "id":       vid_id,
                "title":    r.get("title", "Unknown"),
                "channel":  r.get("channel", ""),
                "duration": r.get("duration", ""),
                "thumb":    r.get("thumbnail", f"https://img.youtube.com/vi/{vid_id}/mqdefault.jpg"),
            })
        return out
    except Exception:
        pass
    return []


async def _get_trending() -> list:
    global _trending_cache, _trending_ts
    now = time.monotonic()
    if _trending_cache and (now - _trending_ts) < _TRENDING_TTL:
        return _trending_cache

    queries = [
        ("hindi",         "Hindi hits 2025", "hindi"),
        ("punjabi",       "Punjabi hits 2025", "punjabi"),
        ("bollywood",     "Bollywood songs 2025", "bollywood"),
        ("international", "Top English hits 2025", "international"),
    ]

    songs: list = []
    seen: set = set()

    async def _fetch(cat_id: str, q: str, cat_label: str):
        results = await _fetch_search(q, limit=8)
        for r in results:
            if r["id"] not in seen:
                seen.add(r["id"])
                songs.append({**r, "category": cat_id})

    await asyncio.gather(*[_fetch(c, q, l) for c, q, l in queries])

    if songs:
        _trending_cache = songs
        _trending_ts = now
    return songs


async def _download_audio(vid: str) -> Optional[str]:
    """Download audio for vid and return local file path (or None on failure)."""
    existing = _find_audio(vid)
    if existing:
        return existing

    lock = _audio_locks.get(vid)
    if lock is None:
        lock = asyncio.Lock()
        _audio_locks[vid] = lock

    async with lock:
        existing = _find_audio(vid)
        if existing:
            return existing
        try:
            loop = asyncio.get_event_loop()
            from KHUSHI.utils.ytdl_smart import smart_download
            d = _download_dir()
            os.makedirs(d, exist_ok=True)
            path = await loop.run_in_executor(None, smart_download, vid, d, "audio")
            return path if path and os.path.isfile(path) else None
        except Exception as e:
            _log.warning(f"[WebAPI] audio download failed for {vid}: {e}")
            return None
        finally:
            _audio_locks.pop(vid, None)


# ── static & health ───────────────────────────────────────────────────────────

async def _handle_index(request: web.Request) -> web.Response:
    try:
        with open(_INDEX, "r", encoding="utf-8") as f:
            html = f.read()
        return web.Response(text=html, content_type="text/html", charset="utf-8")
    except FileNotFoundError:
        return web.Response(text="<h1>Web player not found.</h1>",
                            content_type="text/html", status=404)


async def _handle_health(request: web.Request) -> web.Response:
    return web.Response(text="OK", content_type="text/plain")


async def _handle_static(request: web.Request) -> web.Response:
    filename = request.match_info.get("filename", "")
    path = os.path.join(_WEB_DIR, filename)
    if os.path.isfile(path) and os.path.abspath(path).startswith(os.path.abspath(_WEB_DIR)):
        return web.FileResponse(path)
    raise web.HTTPNotFound()


# ── API: /api/trending ────────────────────────────────────────────────────────

async def _api_trending(request: web.Request) -> web.Response:
    songs = await _get_trending()
    return web.json_response({"songs": songs})


# ── API: /api/status ──────────────────────────────────────────────────────────

async def _api_status(request: web.Request) -> web.Response:
    try:
        from KHUSHI.misc import db
        from KHUSHI.core.call import JARVIS
        chats = []
        for chat_id in list(JARVIS.active_calls):
            queue = db.get(chat_id, [])
            if not queue:
                continue
            cur = queue[0]
            chats.append({
                "chat_id":     chat_id,
                "queue_count": len(queue) - 1,
                "current": {
                    "title":     cur.get("title", ""),
                    "duration":  cur.get("dur", ""),
                    "thumbnail": f"https://img.youtube.com/vi/{cur.get('vidid','')}/mqdefault.jpg",
                    "vidid":     cur.get("vidid", ""),
                    "by":        cur.get("by", ""),
                },
            })
        return web.json_response({"chats": chats, "active_count": len(chats)})
    except Exception as e:
        return web.json_response({"chats": [], "error": str(e)})


# ── API: /api/search ──────────────────────────────────────────────────────────

async def _api_search(request: web.Request) -> web.Response:
    q = request.rel_url.query.get("q", "").strip()
    if not q:
        return web.json_response({"results": [], "error": "missing query"})
    results = await _fetch_search(q, limit=12)
    return web.json_response({"results": results})


# ── API: /api/stream (metadata) ───────────────────────────────────────────────

async def _api_stream(request: web.Request) -> web.Response:
    vid = request.rel_url.query.get("v", "").strip()
    if not vid:
        return web.json_response({"error": "missing v"}, status=400)
    info = {
        "id":    vid,
        "thumb": f"https://img.youtube.com/vi/{vid}/mqdefault.jpg",
        "url":   f"https://www.youtube.com/watch?v={vid}",
    }
    try:
        results = await _fetch_search(f"https://www.youtube.com/watch?v={vid}", limit=1)
        if results:
            info.update(results[0])
    except Exception:
        pass
    return web.json_response(info)


# ── API: /api/audio ───────────────────────────────────────────────────────────

async def _api_audio(request: web.Request) -> web.Response:
    vid = request.rel_url.query.get("v", "").strip()
    if not vid:
        return web.Response(status=400, text="missing v")

    is_probe = request.method == "HEAD" or request.rel_url.query.get("_probe")

    existing = _find_audio(vid)
    if not existing:
        if is_probe:
            # Signal to client: still downloading, retry later
            return web.Response(status=503, text="downloading")
        existing = await _download_audio(vid)

    if not existing or not os.path.isfile(existing):
        return web.Response(status=404, text="audio not found")

    ext = existing.rsplit(".", 1)[-1].lower()
    mime = {
        "m4a": "audio/mp4",
        "mp3": "audio/mpeg",
        "webm": "audio/webm",
        "opus": "audio/ogg",
    }.get(ext, "audio/mpeg")

    if is_probe:
        return web.Response(
            status=200,
            headers={"Content-Type": mime, "Accept-Ranges": "bytes"},
        )

    file_size = os.path.getsize(existing)
    range_header = request.headers.get("Range")

    if range_header:
        try:
            byte_range = range_header.strip().replace("bytes=", "")
            start_s, end_s = byte_range.split("-", 1)
            start = int(start_s) if start_s else 0
            end   = int(end_s)   if end_s   else file_size - 1
            end   = min(end, file_size - 1)
            length = end - start + 1

            def _read_chunk(path, s, l):
                with open(path, "rb") as f:
                    f.seek(s)
                    return f.read(l)

            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, _read_chunk, existing, start, length)
            return web.Response(
                status=206,
                body=data,
                headers={
                    "Content-Type":  mime,
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(length),
                },
            )
        except Exception:
            pass

    return web.FileResponse(
        existing,
        headers={
            "Content-Type":  mime,
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache",
        },
    )


# ── API: /api/video ───────────────────────────────────────────────────────────

async def _api_video(request: web.Request) -> web.Response:
    vid = request.rel_url.query.get("v", "").strip()
    if not vid:
        return web.Response(status=400, text="missing v")

    d = _download_dir()
    for ext in ("mp4", "webm", "mkv"):
        p = os.path.join(d, f"{vid}.{ext}")
        if os.path.isfile(p):
            return web.FileResponse(p, headers={"Accept-Ranges": "bytes"})

    return web.Response(status=404, text="video not found")


# ── API: /api/download ────────────────────────────────────────────────────────

async def _api_download(request: web.Request) -> web.Response:
    vid = request.rel_url.query.get("v", "").strip()
    if not vid:
        return web.Response(status=400, text="missing v")

    existing = _find_audio(vid)
    if not existing:
        existing = await _download_audio(vid)

    if not existing or not os.path.isfile(existing):
        return web.Response(status=404, text="not found")

    ext = existing.rsplit(".", 1)[-1].lower()
    return web.FileResponse(
        existing,
        headers={"Content-Disposition": f'attachment; filename="{vid}.{ext}"'},
    )


# ── API: /api/related ─────────────────────────────────────────────────────────

async def _api_related(request: web.Request) -> web.Response:
    vid = request.rel_url.query.get("v", "").strip()
    if not vid:
        return web.json_response({"results": []})
    try:
        results = await _fetch_search(f"https://www.youtube.com/watch?v={vid}", limit=10)
        if not results:
            results = await _fetch_search("Hindi trending songs", limit=10)
        return web.json_response({"results": results})
    except Exception:
        return web.json_response({"results": []})


# ── App factory ───────────────────────────────────────────────────────────────

def _make_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/",                  _handle_index)
    app.router.add_get("/health",            _handle_health)
    app.router.add_get("/api/trending",      _api_trending)
    app.router.add_get("/api/status",        _api_status)
    app.router.add_get("/api/search",        _api_search)
    app.router.add_get("/api/stream",        _api_stream)
    app.router.add_get("/api/audio",         _api_audio)
    app.router.add_route("HEAD", "/api/audio", _api_audio)
    app.router.add_get("/api/video",         _api_video)
    app.router.add_get("/api/download",      _api_download)
    app.router.add_get("/api/related",       _api_related)
    app.router.add_get("/static/{filename:.+}", _handle_static)
    app.router.add_get("/{filename:.+}",     _handle_static)
    return app


async def start_webserver(host: str, port: int) -> web.AppRunner:
    """Start the aiohttp web server and return the runner (for later cleanup)."""
    try:
        from web_config import WEB_ENABLED
        if not WEB_ENABLED:
            _log.info("Web server disabled via web_config.WEB_ENABLED=False")
            return None
    except ImportError:
        pass

    app = _make_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    _log.info(f"Web player running on http://{host}:{port}")
    return runner
