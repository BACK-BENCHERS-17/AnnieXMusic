import asyncio
import os
import re
from typing import Dict, List, Optional, Tuple, Union

import aiofiles
import aiohttp
from aiohttp import TCPConnector
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from ANNIEMUSIC.core.dir import DOWNLOAD_DIR as _DOWNLOAD_DIR, CACHE_DIR
from ANNIEMUSIC.utils.tuning import CHUNK_SIZE, SEM
from ANNIEMUSIC.utils.ytdl_smart import (
    get_base_ytdlp_opts,
    get_cdn_headers,
    smart_download,
    smart_extract_url,
)
from ANNIEMUSIC.logging import LOGGER
from ANNIEMUSIC.utils.internal_secret import get_secret
from config import API_KEY, API_URL

USE_API: bool = bool(API_URL and API_KEY)

# ── Internal webserver API ─────────────────────────────────────────────────
_WEB_PORT = int(os.environ.get("PORT") or os.environ.get("WEB_PORT") or 8080)
_YTURL_ENDPOINT = f"http://localhost:{_WEB_PORT}/api/yturl"
_YTDL_ENDPOINT  = f"http://localhost:{_WEB_PORT}/api/ytdl"

_inflight: Dict[str, asyncio.Future] = {}
_inflight_lock = asyncio.Lock()

_session: Optional[aiohttp.ClientSession] = None
_session_lock = asyncio.Lock()


def extract_video_id(link: str) -> str:
    if "v=" in link:
        return link.split("v=")[-1].split("&")[0]
    return link.split("/")[-1].split("?")[0]


def file_exists(video_id: str) -> Optional[str]:
    for ext in ("m4a", "mp3", "mp4", "webm", "mkv", "opus", "ogg", "flac"):
        path = f"{_DOWNLOAD_DIR}/{video_id}.{ext}"
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return path
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


async def download_from_cdn_url(vid: str, stream_url: str, ext: str) -> Optional[str]:
    """Download audio from a CDN URL to a local file using matching client headers."""
    out_path = f"{_DOWNLOAD_DIR}/{vid}.{ext}"
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        return out_path
    tmp_path = out_path + ".tmp"
    try:
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


async def download_audio_concurrent(link: str) -> Optional[str]:
    """
    Main audio download function — permanent multi-method approach.

    Method chain (fastest to most robust):
    1. File cache — instant if already downloaded
    2. Internal /api/yturl → CDN download (uses stream cache = near-instant on cache hit)
    3. SmartYTDL URL extract → CDN download (fresh probe if not cached)
    4. SmartYTDL direct download (yt-dlp handles everything internally)
    5. External API race (if configured)
    """
    vid = extract_video_id(link)
    cached = file_exists(vid)
    if cached:
        return cached

    key = f"rac:{link}"

    async def run():
        loop = asyncio.get_running_loop()

        # ── Method 1: Internal /api/yturl → CDN download ───────────────────
        # Uses webserver stream cache — instant if URL was recently fetched
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

        # ── Method 2: SmartYTDL URL extract → CDN download ─────────────────
        # Fresh probe using adaptive multi-client engine
        try:
            info = await loop.run_in_executor(None, smart_extract_url, vid)
            if info:
                cdn_url = info["url"]
                ext = info["ext"]
                local = await download_from_cdn_url(vid, cdn_url, ext)
                if local:
                    LOGGER(__name__).info(
                        f"[SMART] CDN download ok via {info['client']}: {local}"
                    )
                    return local
                LOGGER(__name__).info(f"[SMART] CDN blocked, trying direct download for {vid}")
        except Exception as e:
            LOGGER(__name__).debug(f"[SMART] URL extract failed for {vid}: {e}")

        # ── Method 3: SmartYTDL direct download ────────────────────────────
        # yt-dlp handles auth, rate limits, n-param decoding internally
        try:
            fmt = "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best"
            path = await _with_sem(loop.run_in_executor(None, smart_download, vid, _DOWNLOAD_DIR, fmt))
            if path:
                LOGGER(__name__).info(f"[SMART] Direct download ok: {path}")
                return path
        except Exception as e:
            LOGGER(__name__).debug(f"[SMART] Direct download failed for {vid}: {e}")

        # ── Method 4: External API race (only if configured) ────────────────
        if USE_API:
            try:
                yt_task = asyncio.create_task(yt_dlp_download(link, type="audio"))
                api_task = asyncio.create_task(api_download_song(link))
                done, pending = await asyncio.wait(
                    {yt_task, api_task}, return_when=asyncio.FIRST_COMPLETED
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
                for p in pending:
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
