import asyncio
import os
import re
import time
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse, parse_qs

import aiofiles
import aiohttp
from aiohttp import TCPConnector
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from KHUSHI.core.dir import DOWNLOAD_DIR as _DOWNLOAD_DIR, CACHE_DIR
from KHUSHI.utils.tuning import CHUNK_SIZE, SEM
from KHUSHI.utils.ytdl_smart import (
    get_base_ytdlp_opts,
    get_cdn_headers,
    smart_download,
    smart_extract_url,
)
from KHUSHI.logger_setup import LOGGER
from KHUSHI.utils.internal_secret import get_secret
from config import API_KEY, API_URL

USE_API: bool = bool(API_URL and API_KEY)

# ── In-process CDN URL cache ──────────────────────────────────────────────────
# Stores (url, ext, expires_at) per video ID.
# Avoids re-extraction when prefetch already resolved the URL.
_url_cache: Dict[str, Tuple[str, str, float]] = {}


def _cache_cdn_url(vid: str, url: str, ext: str = "m4a") -> None:
    """Store a CDN URL in the in-process cache with smart TTL from the URL's expire param."""
    try:
        exp_param = parse_qs(urlparse(url).query).get("expire", [None])[0]
        expires_at = int(exp_param) - 300 if exp_param else time.time() + 3600
    except Exception:
        expires_at = time.time() + 3600
    _url_cache[vid] = (url, ext, expires_at)


def _get_cached_cdn_url(vid: str) -> Optional[Tuple[str, str]]:
    """Return (url, ext) from in-process cache if still valid, else None."""
    cached = _url_cache.get(vid)
    if not cached:
        return None
    url, ext, expires_at = cached
    if time.time() < expires_at:
        return url, ext
    _url_cache.pop(vid, None)
    return None

# ── Internal webserver API ─────────────────────────────────────────────────
# webserver.py binds on WEB_PORT (default 5000); health_check.py on 8080.
# We always talk to the main webserver (port 5000) for URL/download APIs.
_WEB_PORT = int(os.environ.get("WEB_PORT") or 5000)
_YTURL_ENDPOINT = f"http://localhost:{_WEB_PORT}/api/yturl"
_YTDL_ENDPOINT  = f"http://localhost:{_WEB_PORT}/api/ytdl"
_PREPARE_ENDPOINT = f"http://localhost:{_WEB_PORT}/api/prepare"

_inflight: Dict[str, asyncio.Future] = {}
_inflight_lock = asyncio.Lock()

_session: Optional[aiohttp.ClientSession] = None
_session_lock = asyncio.Lock()


def extract_video_id(link: str) -> str:
    if "v=" in link:
        return link.split("v=")[-1].split("&")[0]
    return link.split("/")[-1].split("?")[0]


def file_exists(video_id: str) -> Optional[str]:
    import glob as _glob
    for ext in ("m4a", "mp3", "mp4", "webm", "mkv", "opus", "ogg", "flac"):
        # Standard clean filename (current format)
        path = f"{_DOWNLOAD_DIR}/{video_id}.{ext}"
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return path
        # Legacy timestamped filename (vid_ts.ext) — kept for backward compat
        matches = [
            p for p in _glob.glob(f"{_DOWNLOAD_DIR}/{video_id}_*.{ext}")
            if os.path.getsize(p) > 0
        ]
        if matches:
            return max(matches, key=os.path.getmtime)
    return None


def _safe_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]+', "_", (name or "").strip())[:200]


def _ytdlp_base_opts() -> Dict:
    """
    Returns yt-dlp base options using the current best-known working client.
    Powered by SmartYTDL — automatically adapts when YouTube changes its detection.
    """
    opts = get_base_ytdlp_opts(_DOWNLOAD_DIR)
    opts["cachedir"] = str(CACHE_DIR)
    return opts


async def _get_session() -> aiohttp.ClientSession:
    global _session
    if _session and not _session.closed:
        return _session
    async with _session_lock:
        if _session and not _session.closed:
            return _session
        timeout = aiohttp.ClientTimeout(total=600, sock_connect=20, sock_read=60)
        connector = TCPConnector(limit=0, ttl_dns_cache=300, enable_cleanup_closed=True)
        _session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return _session


async def _convert_webm_to_m4a(src: str, vid: str) -> Optional[str]:
    """Convert a webm/opus file to m4a for reliable NTgCalls VC playback."""
    out = f"{_DOWNLOAD_DIR}/{vid}.m4a"
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", src,
            "-vn", "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            out,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        if proc.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0:
            try:
                os.remove(src)
            except Exception:
                pass
            LOGGER(__name__).info(f"[CONV] webm→m4a ok: {out}")
            return out
        LOGGER(__name__).warning(f"[CONV] webm→m4a failed for {vid}: {stderr.decode()[:200]}")
    except Exception as e:
        LOGGER(__name__).warning(f"[CONV] webm→m4a exception for {vid}: {e}")
    return None


async def download_from_cdn_url(vid: str, stream_url: str, ext: str, headers: dict = None) -> Optional[str]:
    """Download audio from a CDN URL to a local file using matching client headers."""
    out_path = f"{_DOWNLOAD_DIR}/{vid}.{ext}"
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        return out_path
    tmp_path = out_path + ".tmp"
    try:
        if headers is None:
            headers = get_cdn_headers()
        timeout = aiohttp.ClientTimeout(total=90, connect=10)
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.get(stream_url, headers=headers) as resp:
                if resp.status not in (200, 206):
                    LOGGER(__name__).warning(f"[CDN] Bad status {resp.status} for {vid}")
                    return None
                async with aiofiles.open(tmp_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(CHUNK_SIZE):
                        if chunk:
                            await f.write(chunk)
        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 1024:
            os.replace(tmp_path, out_path)
            if ext == "webm":
                converted = await _convert_webm_to_m4a(out_path, vid)
                if converted:
                    return converted
            return out_path
    except Exception as e:
        LOGGER(__name__).warning(f"[CDN] Download failed for {vid}: {e}")
        try:
            os.remove(tmp_path)
        except Exception:
            pass
    return None


async def api_get_stream_url(vid: str) -> Optional[Tuple[str, str]]:
    """
    Call the internal webserver API to get a stream URL.
    Returns (url, ext) on success, None on failure.
    """
    try:
        params = {"v": vid, "key": get_secret()}
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.get(_YTURL_ENDPOINT, params=params) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                url = data.get("url", "")
                ext = data.get("ext", "m4a")
                if url:
                    return url, ext
    except Exception as e:
        LOGGER(__name__).debug(f"api_get_stream_url failed for {vid}: {e}")
    return None


async def api_download_song(link: str) -> Optional[str]:
    if not USE_API:
        return None
    vid = extract_video_id(link)
    poll_url = f"{API_URL}/song/{vid}?api={API_KEY}"
    try:
        session = await _get_session()
        while True:
            async with session.get(poll_url) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                s = str(data.get("status", "")).lower()
                if s == "downloading":
                    await asyncio.sleep(1.5)
                    continue
                if s != "done":
                    return None
                dl = data.get("link")
                fmt = str(data.get("format", "mp3")).lower()
                out_path = f"{_DOWNLOAD_DIR}/{vid}.{fmt}"
                async with session.get(dl) as fr:
                    if fr.status != 200:
                        return None
                    async with aiofiles.open(out_path, "wb") as f:
                        async for chunk in fr.content.iter_chunked(CHUNK_SIZE):
                            if not chunk:
                                break
                            await f.write(chunk)
                return out_path
    except Exception:
        return None


async def _with_sem(coro):
    async with SEM:
        return await coro


async def _dedup(key: str, runner):
    async with _inflight_lock:
        fut = _inflight.get(key)
        if fut:
            return await fut
        fut = asyncio.get_running_loop().create_future()
        _inflight[key] = fut
    try:
        res = await runner()
        fut.set_result(res)
        return res
    except Exception as e:
        fut.set_exception(e)
        raise e
    finally:
        async with _inflight_lock:
            _inflight.pop(key, None)


async def yt_dlp_download(
    link: str, type: str, format_id: str = None, title: str = None
) -> Optional[str]:
    loop = asyncio.get_running_loop()
    vid = extract_video_id(link)

    def _do_smart_download(link, fmt, out_path_prefix=None):
        """
        Use SmartYTDL for robust multi-client download.
        Tries cached best client first, then probes all others if needed.
        """
        result = smart_download(vid, _DOWNLOAD_DIR, fmt)
        if result:
            return result
        # Last resort: try the yt-dlp base opts as well (includes top 3 clients)
        opts = _ytdlp_base_opts()
        opts["format"] = fmt
        if out_path_prefix:
            opts["outtmpl"] = f"{_DOWNLOAD_DIR}/{out_path_prefix}.%(ext)s"
        try:
            with YoutubeDL(opts) as ydl:
                ydl.download([link])
        except Exception as e:
            LOGGER(__name__).error(f"[DL] Final fallback failed for {vid}: {e}")
        return file_exists(vid)

    if type == "audio":
        key = f"a:{link}"

        async def run():
            fmt = "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best"
            res = await _with_sem(loop.run_in_executor(None, _do_smart_download, link, fmt))
            return res

        return await _dedup(key, run)

    if type == "video":
        key = f"v:{link}"

        async def run():
            fmt = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]/best"

            def _do():
                opts = _ytdlp_base_opts()
                opts.update({
                    "format": fmt,
                    "prefer_ffmpeg": True,
                    "merge_output_format": "mp4",
                })
                try:
                    with YoutubeDL(opts) as ydl:
                        ydl.download([link])
                except DownloadError as e:
                    if "Requested format is not available" in str(e):
                        opts["format"] = "bestvideo+bestaudio/best"
                        try:
                            with YoutubeDL(opts) as ydl:
                                ydl.download([link])
                        except Exception:
                            pass
                except Exception as e:
                    LOGGER(__name__).error(f"[DL] video error for {vid}: {e}")
                return file_exists(vid)

            return await _with_sem(loop.run_in_executor(None, _do))

        return await _dedup(key, run)

    if type == "song_video" and format_id and title:
        safe_title = _safe_filename(title)
        key = f"sv:{link}:{format_id}:{safe_title}"

        async def run():
            def _do():
                fmt = f"{format_id}+bestaudio[ext=m4a]/{format_id}+bestaudio/bestvideo[height<=720]+bestaudio/best"
                opts = _ytdlp_base_opts()
                opts.update({
                    "format": fmt,
                    "outtmpl": f"{_DOWNLOAD_DIR}/{safe_title}.%(ext)s",
                    "prefer_ffmpeg": True,
                    "merge_output_format": "mp4",
                    "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
                })
                try:
                    with YoutubeDL(opts) as ydl:
                        ydl.extract_info(link, download=True)
                except DownloadError as de:
                    try:
                        opts["format"] = "bestvideo[height<=720]+bestaudio/best"
                        with YoutubeDL(opts) as ydl:
                            ydl.extract_info(link, download=True)
                    except Exception as fe:
                        LOGGER(__name__).error(f"[DL] song_video fallback: {fe}")
                except Exception as e:
                    LOGGER(__name__).error(f"[DL] song_video: {e}")

                for ext in ("mp4", "mkv", "webm", "mov"):
                    p = f"{_DOWNLOAD_DIR}/{safe_title}.{ext}"
                    if os.path.exists(p) and os.path.getsize(p) > 0:
                        return p
                return None

            return await _with_sem(loop.run_in_executor(None, _do))

        return await _dedup(key, run)

    if type == "song_audio" and format_id and title:
        safe_title = _safe_filename(title)
        key = f"sa:{link}:{format_id}:{safe_title}"

        async def run():
            def _do():
                opts = _ytdlp_base_opts()
                opts.update({
                    "format": f"{format_id}/bestaudio[ext=m4a]/bestaudio/best",
                    "outtmpl": f"{_DOWNLOAD_DIR}/{safe_title}.%(ext)s",
                })
                try:
                    with YoutubeDL(opts) as ydl:
                        ydl.extract_info(link, download=True)
                except DownloadError as de:
                    LOGGER(__name__).warning(f"[DL] song_audio DownloadError: {de}")
                except Exception as e:
                    LOGGER(__name__).error(f"[DL] song_audio error: {e}")

                for ext in ("m4a", "webm", "opus", "ogg", "mp3"):
                    p = f"{_DOWNLOAD_DIR}/{safe_title}.{ext}"
                    if os.path.exists(p) and os.path.getsize(p) > 0:
                        return p
                return None

            return await _with_sem(loop.run_in_executor(None, _do))

        return await _dedup(key, run)

    return None


async def download_from_own_api(vid: str) -> Optional[str]:
    """Call internal webserver /api/ytdl to download audio as MP3."""
    out_path = f"{_DOWNLOAD_DIR}/{vid}.mp3"
    if os.path.exists(out_path) and os.path.getsize(out_path) > 1024:
        return out_path
    try:
        url = f"{_YTDL_ENDPOINT}?v={vid}&key={get_secret()}"
        timeout = aiohttp.ClientTimeout(total=180, connect=5)
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.get(url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                path = data.get("path")
                if path and os.path.exists(path) and os.path.getsize(path) > 1024:
                    LOGGER(__name__).info(f"[YTDL-API] MP3 ready: {path}")
                    return path
    except Exception as e:
        LOGGER(__name__).debug(f"[YTDL-API] Failed for {vid}: {e}")
    return None


_bg_download_tasks: Dict[str, asyncio.Task] = {}


async def _trigger_bg_cache(vid: str) -> None:
    """Start a background download to cache the file locally for future plays."""
    if file_exists(vid):
        return
    if vid in _bg_download_tasks:
        t = _bg_download_tasks[vid]
        if not t.done():
            return

    async def _bg():
        try:
            # Also tell the webserver to download in its own thread pool
            try:
                params = {"v": vid, "key": get_secret()}
                timeout = aiohttp.ClientTimeout(total=5)
                async with aiohttp.ClientSession(timeout=timeout) as s:
                    await s.get(_PREPARE_ENDPOINT, params=params)
            except Exception:
                pass
            loop = asyncio.get_running_loop()
            fmt = "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best"
            path = await loop.run_in_executor(None, smart_download, vid, _DOWNLOAD_DIR, fmt)
            if path:
                LOGGER(__name__).info(f"[BG-CACHE] Cached for next play: {path}")
                # Save absolute file path to MongoDB permanently so any restart
                # finds the file instantly without re-downloading or re-extracting.
                try:
                    from KHUSHI.utils.url_cache import put_file_path as _pfp
                    await _pfp(vid, os.path.abspath(path))
                except Exception:
                    pass
        except asyncio.CancelledError:
            pass
        except Exception as e:
            LOGGER(__name__).debug(f"[BG-CACHE] Failed for {vid}: {e}")
        finally:
            _bg_download_tasks.pop(vid, None)

    task = asyncio.create_task(_bg())
    _bg_download_tasks[vid] = task


async def fast_get_stream(vid: str) -> Optional[str]:
    """
    Return a file path or CDN URL for the given YouTube video ID as fast as possible.

    Priority:
      1. Cached local file             → instant (0 ms)
      2. In-process CDN URL cache      → instant (<1 ms) — set by prefetch or prior plays
      3. MongoDB persistent URL cache  → ~10-50 ms — shared across restarts and all users
      4. Webserver cache + SmartYTDL extraction run IN PARALLEL:
         - Webserver hits  → returns immediately (~10 ms)
         - Webserver miss  → SmartYTDL extraction already running → returns in 5-8 s
      5. Full local download fallback  → only if all extraction paths fail

    Every successfully extracted URL is saved to MongoDB so any future request
    (by any user, even after a restart) for the same song is near-instant.
    """
    from KHUSHI.utils.url_cache import (
        get_url as _mongo_get, put_url as _mongo_put,
        get_file_path as _mongo_get_file, put_file_path as _mongo_put_file,
    )

    # ── 1. Local file on disk (fastest path) ──────────────────────────────────
    cached = file_exists(vid)
    if cached:
        return cached

    # ── 2. MongoDB file path cache (permanent — survives CDN expiry + restart) ─
    # When background download finishes, it saves the absolute path to MongoDB.
    # After any restart, as long as the file still exists on disk, this is instant.
    try:
        mongo_file = await _mongo_get_file(vid)
        if mongo_file:
            LOGGER(__name__).info(f"[FAST] MongoDB FILE cache hit for {vid}: {mongo_file}")
            asyncio.create_task(_trigger_bg_cache(vid))   # refresh if needed
            return mongo_file
    except Exception as e:
        LOGGER(__name__).debug(f"[FAST] MongoDB file cache check failed for {vid}: {e}")

    # ── 3. In-process URL cache (sub-millisecond, lost on restart) ─────────────
    hit = _get_cached_cdn_url(vid)
    if hit:
        cdn_url, _ext = hit
        LOGGER(__name__).info(f"[FAST] In-process URL cache hit for {vid}")
        asyncio.create_task(_trigger_bg_cache(vid))
        return cdn_url

    # ── 4. MongoDB URL cache (~30ms — shared across users, 6h TTL) ────────────
    try:
        mongo_hit = await _mongo_get(vid)
        if mongo_hit:
            cdn_url, ext = mongo_hit
            _cache_cdn_url(vid, cdn_url, ext)
            LOGGER(__name__).info(f"[FAST] MongoDB URL cache hit for {vid}")
            asyncio.create_task(_trigger_bg_cache(vid))
            return cdn_url
    except Exception as e:
        LOGGER(__name__).debug(f"[FAST] MongoDB URL cache check failed for {vid}: {e}")

    loop = asyncio.get_running_loop()

    async def _webserver_check():
        try:
            result = await api_get_stream_url(vid)
            if result:
                cdn_url, ext = result
                _cache_cdn_url(vid, cdn_url, ext)
                asyncio.create_task(_mongo_put(vid, cdn_url, ext))
                LOGGER(__name__).info(f"[FAST] Webserver cache hit for {vid}")
                return cdn_url
        except Exception as e:
            LOGGER(__name__).debug(f"[FAST] Webserver URL cache miss for {vid}: {e}")
        return None

    async def _extract():
        try:
            info = await loop.run_in_executor(None, smart_extract_url, vid)
            if info and info.get("url"):
                cdn_url = info["url"]
                ext = info.get("ext", "m4a")
                _cache_cdn_url(vid, cdn_url, ext)
                asyncio.create_task(_mongo_put(vid, cdn_url, ext))
                LOGGER(__name__).info(
                    f"[FAST] SmartYTDL extracted URL for {vid} via {info.get('client', '?')}"
                )
                return cdn_url
        except Exception as e:
            LOGGER(__name__).debug(f"[FAST] URL extraction failed for {vid}: {e}")
        return None

    # Race webserver cache check vs fresh extraction — both start at t=0.
    # First non-None result wins. If webserver hits (~10 ms), extraction is cancelled.
    # If webserver misses (~10-50 ms), extraction is already 50 ms into running.
    tasks = [
        asyncio.create_task(_webserver_check()),
        asyncio.create_task(_extract()),
    ]
    url = None
    for coro in asyncio.as_completed(tasks):
        try:
            result = await coro
            if result:
                url = result
                break
        except Exception:
            pass

    # Cancel any still-running tasks
    for t in tasks:
        if not t.done():
            t.cancel()

    if url:
        asyncio.create_task(_trigger_bg_cache(vid))
        return url

    # ── Check if background cache completed during URL extraction ───────────────
    cached_now = file_exists(vid)
    if cached_now:
        LOGGER(__name__).info(f"[FAST] BG cache hit after extraction for {vid}")
        return cached_now

    # ── Wait for in-flight BG download task — avoids duplicate full download ───
    # The BG task (started by _trigger_bg_cache in play.py) runs smart_download
    # which uses _direct_download. If it's still running, wait for it instead of
    # kicking off another identical download — saves 10-15 seconds on cache miss.
    bg_task = _bg_download_tasks.get(vid)
    if bg_task and not bg_task.done():
        LOGGER(__name__).info(f"[FAST] Waiting for in-flight BG task for {vid}")
        try:
            await asyncio.wait_for(asyncio.shield(bg_task), timeout=35.0)
        except Exception:
            pass
        cached_after_bg = file_exists(vid)
        if cached_after_bg:
            LOGGER(__name__).info(f"[FAST] BG task completed, using: {cached_after_bg}")
            return cached_after_bg

    # ── Full download fallback (only if BG task also failed or doesn't exist) ──
    LOGGER(__name__).warning(f"[FAST] All URL methods failed for {vid}, falling back to full download")
    link_full = f"https://www.youtube.com/watch?v={vid}"
    path = await download_audio_concurrent(link_full)
    if path:
        LOGGER(__name__).info(f"[FAST] Fallback download done: {path}")
    return path


def _kick_bg_download(vid: str, link: str) -> None:
    """Fire-and-forget background download to cache the file locally."""
    if vid in _bg_download_tasks:
        t = _bg_download_tasks[vid]
        if not t.done():
            return

    async def _bg():
        try:
            loop = asyncio.get_running_loop()
            fmt = "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best"
            path = await loop.run_in_executor(None, smart_download, vid, _DOWNLOAD_DIR, fmt)
            if path:
                LOGGER(__name__).info(f"[BG-DL] Cached for future plays: {path}")
        except Exception as e:
            LOGGER(__name__).debug(f"[BG-DL] Background download failed for {vid}: {e}")
        finally:
            _bg_download_tasks.pop(vid, None)

    try:
        task = asyncio.get_event_loop().create_task(_bg())
        _bg_download_tasks[vid] = task
    except Exception:
        pass


async def download_audio_concurrent(link: str) -> Optional[str]:
    """
    Main audio download function — parallel CDN + direct download race.

    Flow:
    1. File cache — instant if already downloaded
    2. CDN path + Direct download run IN PARALLEL — first to finish wins
       CDN path: Internal /api/yturl → CDN download (near-instant on cache hit)
                 Fallback: fresh SmartYTDL URL extract → CDN download
       Direct:   SmartYTDL direct yt-dlp download (always works, 10-25s)
    3. External API race (only if API_URL configured)

    Parallel approach ensures: if CDN gets 403 after 2s, direct download
    is already 2s into its run → total wait ~15s instead of 40-50s.
    """
    vid = extract_video_id(link)
    cached = file_exists(vid)
    if cached:
        return cached

    key = f"rac:{link}"

    async def run():
        loop = asyncio.get_running_loop()
        from KHUSHI.utils.ytdl_smart import _CLIENT_UA, _JSLESS_CLIENTS

        def _client_headers(client: str) -> dict:
            """Return CDN headers matching the client that extracted the URL."""
            ua = _CLIENT_UA.get(client, _CLIENT_UA.get("android_vr", ""))
            return {
                "User-Agent": ua,
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "identity",
                "Referer": "https://www.youtube.com/",
                "Origin": "https://www.youtube.com",
            }

        # ── CDN path (fast — tries cached URL then fresh extract) ──────────
        async def _cdn_path() -> Optional[str]:
            # Step A: Cached URL from internal webserver
            try:
                result = await api_get_stream_url(vid)
                if result:
                    cdn_url, ext = result
                    local = await download_from_cdn_url(vid, cdn_url, ext)
                    if local:
                        LOGGER(__name__).info(f"[OWN-API] CDN download ok: {local}")
                        return local
                    LOGGER(__name__).info(f"[OWN-API] CDN blocked, falling through for {vid}")
            except Exception as e:
                LOGGER(__name__).debug(f"[OWN-API] yturl failed for {vid}: {e}")

            # Step B: Fresh SmartYTDL extract → CDN download with matching headers
            try:
                info = await loop.run_in_executor(None, smart_extract_url, vid)
                if info:
                    cdn_url = info["url"]
                    ext = info["ext"]
                    client = info.get("client", "android_vr")
                    _cache_cdn_url(vid, cdn_url, ext)
                    hdrs = _client_headers(client)
                    local = await download_from_cdn_url(vid, cdn_url, ext, headers=hdrs)
                    if local:
                        LOGGER(__name__).info(
                            f"[SMART] CDN download ok via {client}: {local}"
                        )
                        return local
                    LOGGER(__name__).info(f"[SMART] CDN blocked for {vid}")
            except Exception as e:
                LOGGER(__name__).debug(f"[SMART] URL extract failed for {vid}: {e}")

            return None

        # ── Direct download (reliable but slower — yt-dlp handles everything) ─
        async def _direct_path() -> Optional[str]:
            try:
                fmt = "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best"
                path = await loop.run_in_executor(None, smart_download, vid, _DOWNLOAD_DIR, fmt)
                if path:
                    LOGGER(__name__).info(f"[SMART] Direct download ok: {path}")
                    return path
            except Exception as e:
                LOGGER(__name__).debug(f"[SMART] Direct download failed for {vid}: {e}")
            return None

        # ── Race: CDN and Direct in parallel — whoever finishes first wins ──
        cdn_task    = asyncio.create_task(_cdn_path())
        direct_task = asyncio.create_task(_direct_path())

        done, pending = await asyncio.wait(
            {cdn_task, direct_task}, return_when=asyncio.FIRST_COMPLETED
        )
        for t in done:
            try:
                res = t.result()
                if res:
                    for p in pending:
                        p.cancel()
                    return res
            except Exception:
                pass

        # One task finished with None — wait for the other
        for p in pending:
            try:
                res = await p
                if res:
                    return res
            except Exception:
                pass

        # ── External API race (only if configured) ──────────────────────────
        if USE_API:
            try:
                yt_task  = asyncio.create_task(yt_dlp_download(link, type="audio"))
                api_task = asyncio.create_task(api_download_song(link))
                done2, pending2 = await asyncio.wait(
                    {yt_task, api_task}, return_when=asyncio.FIRST_COMPLETED
                )
                for t in done2:
                    try:
                        res = t.result()
                        if res:
                            for p in pending2:
                                p.cancel()
                            return res
                    except Exception:
                        pass
                for p in pending2:
                    try:
                        res = await p
                        if res:
                            return res
                    except Exception:
                        pass
            except Exception as e:
                LOGGER(__name__).debug(f"[API-RACE] Failed for {vid}: {e}")

        LOGGER(__name__).error(f"[DL] All methods failed for {vid}")
        return None

    return await _dedup(key, lambda: _with_sem(run()))
