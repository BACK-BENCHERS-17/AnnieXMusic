import asyncio
import contextlib
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
from ANNIEMUSIC.logging import LOGGER
from config import API_KEY, API_URL, BOT_TOKEN

USE_API: bool = bool(API_URL and API_KEY)

# ── Internal webserver API ─────────────────────────────────────────────────
_WEB_PORT = int(os.environ.get("PORT") or os.environ.get("WEB_PORT") or 8080)
_YTURL_ENDPOINT = f"http://localhost:{_WEB_PORT}/api/yturl"

_inflight: Dict[str, asyncio.Future] = {}


async def api_get_stream_url(vid: str) -> Optional[Tuple[str, str]]:
    """
    Call the internal webserver API to get a stream URL fast (~2s).
    Returns (url, ext) on success, None on failure.
    Both the bot and webserver run on the same Railway service → localhost works.
    """
    try:
        params = {"v": vid, "key": BOT_TOKEN or ""}
        timeout = aiohttp.ClientTimeout(total=8)
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


def _ytdlp_base_opts() -> Dict[str, Union[str, int, bool, Dict, List]]:
    """Base yt-dlp options using android_vr client — no cookies needed on Replit/cloud."""
    return {
        "outtmpl": f"{_DOWNLOAD_DIR}/%(id)s.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "overwrites": True,
        "continuedl": True,
        "noprogress": True,
        "cachedir": str(CACHE_DIR),
        "nocheckcertificate": True,
        "source_address": "0.0.0.0",
        "extractor_args": {
            "youtube": {
                "player_client": ["android_vr"],
            }
        },
    }


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
    """Download audio from a CDN URL to a local file. Fast (~1-3s) and reliable."""
    out_path = f"{_DOWNLOAD_DIR}/{vid}.{ext}"
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        return out_path
    tmp_path = out_path + ".tmp"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.youtube.com/",
            "Accept": "*/*",
        }
        timeout = aiohttp.ClientTimeout(total=60, connect=10)
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.get(stream_url, headers=headers) as resp:
                if resp.status not in (200, 206):
                    LOGGER(__name__).warning(f"CDN download bad status for {vid}: {resp.status}")
                    return None
                async with aiofiles.open(tmp_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(CHUNK_SIZE):
                        if chunk:
                            await f.write(chunk)
        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
            os.replace(tmp_path, out_path)
            if ext == "webm":
                converted = await _convert_webm_to_m4a(out_path, vid)
                if converted:
                    return converted
            return out_path
    except Exception as e:
        LOGGER(__name__).warning(f"CDN download failed for {vid}: {e}")
        try:
            os.remove(tmp_path)
        except Exception:
            pass
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


def _download_ytdlp(link: str, opts: Dict) -> Optional[str]:
    try:
        with YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(link, download=False)
            except DownloadError as e:
                if "Requested format is not available" in str(e):
                    opts["format"] = "best"
                    info = ydl.extract_info(link, download=False)
                else:
                    raise e
            
            if not info:
                return None
            
            ext = info.get("ext") or "webm"
            vid = info.get("id")
            path = f"{_DOWNLOAD_DIR}/{vid}.{ext}"
            if os.path.exists(path):
                return path
            ydl.download([link])
            return path
    except Exception as e:
        LOGGER(__name__).error(f"Download failed for {link}: {e}")
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

    def download_with_fallback(link, opts):
        try:
            with YoutubeDL(opts) as ydl:
                ydl.download([link])
                return True
        except DownloadError as e:
            if "Requested format is not available" in str(e):
                LOGGER(__name__).warning(f"Requested format {format_id} not available, falling back to best.")
                # Fallback to best
                if "format" in opts:
                    if type == "song_video":
                        opts["format"] = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best"
                        opts["prefer_ffmpeg"] = True
                        opts["merge_output_format"] = "mp4"
                    elif type == "video":
                        opts["format"] = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
                        opts["prefer_ffmpeg"] = True
                        opts["merge_output_format"] = "mp4"
                    elif type == "song_audio":
                        opts["format"] = "bestaudio/best"
                    else:
                        opts["format"] = "best"
                
                try:
                    with YoutubeDL(opts) as ydl:
                        ydl.download([link])
                        return True
                except Exception as e2:
                    LOGGER(__name__).error(f"Fallback download failed: {e2}")
                    return False
            else:
                LOGGER(__name__).error(f"Download failed: {e}")
                return False
        except Exception as e:
            LOGGER(__name__).error(f"Unexpected download error: {e}")
            return False

    if type == "audio":
        key = f"a:{link}"

        async def run():
            opts = _ytdlp_base_opts()
            opts.update({
                "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
            })
            res = await _with_sem(
                loop.run_in_executor(None, download_with_fallback, link, opts)
            )
            if res:
                vid = extract_video_id(link)
                return file_exists(vid)
            return None

        return await _dedup(key, run)

    if type == "video":
        key = f"v:{link}"

        async def run():
            opts = _ytdlp_base_opts()
            opts.update({
                "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720][vcodec!=none][acodec!=none]/best[height<=720]/best",
                "prefer_ffmpeg": True,
                "merge_output_format": "mp4",
            })
            res = await _with_sem(
                loop.run_in_executor(None, download_with_fallback, link, opts)
            )
            if res:
                vid = extract_video_id(link)
                return file_exists(vid)
            return None

        return await _dedup(key, run)

    if type == "song_video" and format_id and title:
        safe_title = _safe_filename(title)
        key = f"sv:{link}:{format_id}:{safe_title}"

        async def run():
            opts = _ytdlp_base_opts()
            opts.update(
                {
                    "format": f"{format_id}+bestaudio[ext=m4a]/{format_id}+bestaudio/bestvideo[height<=720]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]/best",
                    "outtmpl": f"{_DOWNLOAD_DIR}/{safe_title}.%(ext)s",
                    "prefer_ffmpeg": True,
                    "merge_output_format": "mp4",
                    "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
                }
            )

            def _do_video_download(lnk, o):
                try:
                    with YoutubeDL(o) as ydl:
                        info = ydl.extract_info(lnk, download=True)
                        if not info:
                            return None
                    # Check for merged mp4 first, then any video format
                    mp4_path = f"{_DOWNLOAD_DIR}/{safe_title}.mp4"
                    if os.path.exists(mp4_path) and os.path.getsize(mp4_path) > 0:
                        return mp4_path
                    for e in ("mkv", "webm", "mp4", "mov"):
                        p = f"{_DOWNLOAD_DIR}/{safe_title}.{e}"
                        if os.path.exists(p) and os.path.getsize(p) > 0:
                            return p
                except DownloadError as de:
                    LOGGER(__name__).warning(f"song_video DownloadError: {de}")
                    # Try fallback with bestvideo+bestaudio only
                    try:
                        o["format"] = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best"
                        with YoutubeDL(o) as ydl:
                            ydl.extract_info(lnk, download=True)
                        mp4_path = f"{_DOWNLOAD_DIR}/{safe_title}.mp4"
                        if os.path.exists(mp4_path) and os.path.getsize(mp4_path) > 0:
                            return mp4_path
                        for e in ("mkv", "webm", "mp4", "mov"):
                            p = f"{_DOWNLOAD_DIR}/{safe_title}.{e}"
                            if os.path.exists(p) and os.path.getsize(p) > 0:
                                return p
                    except Exception as fe:
                        LOGGER(__name__).error(f"song_video fallback error: {fe}")
                except Exception as e:
                    LOGGER(__name__).error(f"song_video error: {e}")
                return None

            return await _with_sem(
                loop.run_in_executor(None, _do_video_download, link, opts)
            )

        return await _dedup(key, run)

    if type == "song_audio" and format_id and title:
        safe_title = _safe_filename(title)
        key = f"sa:{link}:{format_id}:{safe_title}"

        async def run():
            opts = _ytdlp_base_opts()
            opts.update(
                {
                    "format": f"{format_id}/bestaudio[ext=m4a]/bestaudio/best",
                    "outtmpl": f"{_DOWNLOAD_DIR}/{safe_title}.%(ext)s",
                }
            )

            def _do_download(lnk, o):
                try:
                    with YoutubeDL(o) as ydl:
                        info = ydl.extract_info(lnk, download=True)
                        if not info:
                            return None
                        ext = info.get("ext") or "m4a"
                        out = f"{_DOWNLOAD_DIR}/{safe_title}.{ext}"
                        if os.path.exists(out) and os.path.getsize(out) > 0:
                            return out
                        # yt-dlp may merge to the final filename; scan
                        for e in ("m4a", "webm", "opus", "ogg", "mp3"):
                            p = f"{_DOWNLOAD_DIR}/{safe_title}.{e}"
                            if os.path.exists(p) and os.path.getsize(p) > 0:
                                return p
                except DownloadError as de:
                    LOGGER(__name__).warning(f"song_audio DownloadError: {de}")
                except Exception as e:
                    LOGGER(__name__).error(f"song_audio error: {e}")
                return None

            res = await _with_sem(
                loop.run_in_executor(None, _do_download, link, opts)
            )
            return res

        return await _dedup(key, run)

    return None


_SHRUTI_API = "https://shrutibots.site"


async def download_from_shruti_api(vid: str) -> Optional[str]:
    """Download audio via shrutibots.site API — returns clean MP3 file."""
    out_path = f"{_DOWNLOAD_DIR}/{vid}.mp3"
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        return out_path
    tmp_path = out_path + ".tmp"
    try:
        tok_timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=tok_timeout) as sess:
            async with sess.get(
                f"{_SHRUTI_API}/download",
                params={"url": vid, "type": "audio"},
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                token = data.get("download_token")
                if not token:
                    return None

            stream_url = f"{_SHRUTI_API}/stream/{vid}?type=audio&token={token}"
            dl_timeout = aiohttp.ClientTimeout(total=180, connect=15)
            async with aiohttp.ClientSession(timeout=dl_timeout) as dl_sess:
                async with dl_sess.get(stream_url, allow_redirects=True) as file_resp:
                    if file_resp.status not in (200, 206):
                        return None
                    async with aiofiles.open(tmp_path, "wb") as f:
                        async for chunk in file_resp.content.iter_chunked(16384):
                            if chunk:
                                await f.write(chunk)

        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 1024:
            os.replace(tmp_path, out_path)
            LOGGER(__name__).info(f"[SHRUTI] MP3 downloaded: {out_path}")
            return out_path
    except Exception as e:
        LOGGER(__name__).debug(f"[SHRUTI] API failed for {vid}: {e}")
        try:
            os.remove(tmp_path)
        except Exception:
            pass
    return None


async def download_audio_concurrent(link: str) -> Optional[str]:
    vid = extract_video_id(link)
    cached = file_exists(vid)
    if cached:
        return cached

    key = f"rac:{link}"

    async def run():
        # 1. Try shrutibots.site API — fast, returns clean MP3 (best VC format)
        try:
            shruti = await download_from_shruti_api(vid)
            if shruti:
                return shruti
        except Exception as e:
            LOGGER(__name__).debug(f"[SHRUTI] path failed for {vid}: {e}")

        # 2. Try internal webserver API — get CDN URL, then download to local file
        #    Local file gives smooth uninterrupted playback in VC (no CDN latency)
        try:
            cdn = await api_get_stream_url(vid)
            if cdn:
                cdn_url, ext = cdn
                local = await download_from_cdn_url(vid, cdn_url, ext)
                if local:
                    LOGGER(__name__).info(
                        f"[STREAM] CDN download ok → local file: {local} ({ext})"
                    )
                    return local
        except Exception as e:
            LOGGER(__name__).debug(f"[STREAM] CDN path failed for {vid}: {e}")

        # 3. External API race (only if configured)
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
                LOGGER(__name__).debug(f"[STREAM] API race failed for {vid}: {e}")

        # 4. Direct yt-dlp download (reliable local-file fallback)
        LOGGER(__name__).info(f"[STREAM] Falling back to yt-dlp local download for {vid}")
        return await yt_dlp_download(link, type="audio")

    return await _dedup(key, lambda: _with_sem(run()))
