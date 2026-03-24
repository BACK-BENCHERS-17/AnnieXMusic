"""
SmartYTDL — Permanent, auto-healing YouTube bypass for cloud servers.

BYPASS LAYERS (tried in order, auto-heals when one breaks):
  1.  Proxy support  — set YTDL_PROXY env var (socks5/http) for IP bypass
  2.  Cookies        — set YOUTUBE_COOKIES_B64 env var (base64 cookies.txt)
                       OR place cookies.txt / youtube_cookies.txt in project root
  3.  10 YouTube player clients tried in PARALLEL — cached best first
  4.  Invidious public API  — no IP restrictions (auto-rotates instances)
  5.  Piped.video API       — another YouTube proxy network
  6.  Auto-healing: broken clients/instances marked, retried after cool-down

Add more Invidious instances to _INVIDIOUS_INSTANCES or more Piped instances
to _PIPED_INSTANCES without touching any other file.
"""

import base64
import logging
import os
import random
import threading
import time
from typing import Dict, List, Optional, Tuple
import yt_dlp

_log = logging.getLogger(__name__)

# ── Proxy support ───────────────────────────────────────────────────────────────
# Set YTDL_PROXY env var to a socks5 or http proxy to bypass IP blocks.
# Example: YTDL_PROXY=socks5://user:pass@proxy.example.com:1080
_PROXY = os.environ.get("YTDL_PROXY") or os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or ""

# ── YouTube player clients (ordered by reliability on cloud IPs) ───────────────
ALL_CLIENTS: List[str] = [
    # NO PO Token required (most reliable on cloud IPs in 2026)
    "android_embed",   # Android embedded — no PO token, MOST RELIABLE
    "android_music",   # YouTube Music Android — no PO token needed
    "tv_embedded",     # TV embedded — no PO token, bypasses restrictions
    "android_vr",      # Android VR — no PO token
    "tv",              # Smart TV client — no PO token
    "web_creator",     # YouTube Studio — reduced restrictions
    # Require GVS PO Token (fallback)
    "ios",             # iPhone app
    "mweb",            # Mobile web
    "web_embedded",    # Embedded web player
    "web",             # Desktop web
]

_CLIENT_UA: Dict[str, str] = {
    "ios":           "com.google.ios.youtube/19.29.1 (iPhone16,2; U; CPU iOS 17_5_1 like Mac OS X;)",
    "mweb":          "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "android_embed": "com.google.android.youtube/19.29.37 (Linux; U; Android 14; en_US; Pixel 8; Build/UQ1A.240105.004;) gzip",
    "tv_embedded":   "Mozilla/5.0 (SMART-TV; Linux; Tizen 6.0) AppleWebKit/538.1 (KHTML, like Gecko) SamsungBrowser/3.0 TV Safari/538.1",
    "android_music": "com.google.android.apps.youtube.music/7.11.52 (Linux; U; Android 14) gzip",
    "android_vr":    "com.google.android.apps.youtube.vr.oculus/1.57.29 (Linux; U; Android 10; Quest) gzip",
    "web_creator":   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.118 Safari/537.36",
    "tv":            "Mozilla/5.0 (SMART-TV; Linux; Tizen 6.0) AppleWebKit/538.1 (KHTML, like Gecko) Version/6.0 TV Safari/538.1",
    "web_embedded":  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.118 Safari/537.36",
    "web":           "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.118 Safari/537.36",
}
_DEFAULT_UA = _CLIENT_UA["android_embed"]

# ── Invidious public instances (auto-rotated on failure) ───────────────────────
# These proxy YouTube traffic — not subject to the same IP restrictions.
# Verified working as of March 2026.
_INVIDIOUS_INSTANCES = [
    "https://iv.ggtyler.dev",
    "https://invidious.protokolla.fi",
    "https://inv.in.projectsegfau.lt",
    "https://invidious.perennialte.ch",
    "https://inv.nadeko.net",
    "https://invidious.nerdvpn.de",
    "https://invidious.incogniweb.net",
    "https://iv.datura.network",
    "https://invidious.io.lol",
    "https://invidious.fdn.fr",
    "https://yewtu.be",
    "https://invidious.slipfox.xyz",
    "https://invidious.privacydev.net",
    "https://invidious.lunar.icu",
    "https://yt.cdaut.de",
]
_invidious_lock = threading.Lock()
_invidious_failed: Dict[str, float] = {}
_INVIDIOUS_FAIL_TTL = 600  # retry a failed instance after 10 min


# ── Piped.video API instances (additional YouTube proxy network) ───────────────
_PIPED_INSTANCES = [
    "https://pipedapi.in.projectsegfau.lt",
    "https://pipedapi.adminforge.de",
    "https://pipedapi.kavin.rocks",
    "https://pipedapi.tokhmi.xyz",
    "https://pipedapi.moomoo.me",
    "https://piped-api.garudalinux.org",
    "https://api.piped.yt",
]
_piped_lock = threading.Lock()
_piped_failed: Dict[str, float] = {}
_PIPED_FAIL_TTL = 600


def _get_invidious_instances() -> List[str]:
    now = time.time()
    with _invidious_lock:
        good = [i for i in _INVIDIOUS_INSTANCES if (now - _invidious_failed.get(i, 0)) > _INVIDIOUS_FAIL_TTL]
        bad  = [i for i in _INVIDIOUS_INSTANCES if i not in good]
    random.shuffle(good)
    return good + bad


def _mark_invidious_failed(instance: str) -> None:
    with _invidious_lock:
        _invidious_failed[instance] = time.time()


def _get_piped_instances() -> List[str]:
    now = time.time()
    with _piped_lock:
        good = [i for i in _PIPED_INSTANCES if (now - _piped_failed.get(i, 0)) > _PIPED_FAIL_TTL]
        bad  = [i for i in _PIPED_INSTANCES if i not in good]
    random.shuffle(good)
    return good + bad


def _mark_piped_failed(instance: str) -> None:
    with _piped_lock:
        _piped_failed[instance] = time.time()


# ── Cookie file support ─────────────────────────────────────────────────────────
_COOKIE_PATHS = [
    os.path.join(os.path.dirname(__file__), "..", "..", "youtube_cookies.txt"),
    os.path.join(os.path.dirname(__file__), "..", "..", "cookies.txt"),
    "/app/youtube_cookies.txt",
    "/app/cookies.txt",
    "/tmp/youtube_cookies.txt",
]

_cookie_file_cache: Optional[str] = None
_cookie_file_ts: float = 0.0
_COOKIE_RECHECK = 120


def _find_cookie_file() -> Optional[str]:
    global _cookie_file_cache, _cookie_file_ts
    now = time.time()

    # Check if we should reload
    if now - _cookie_file_ts < _COOKIE_RECHECK and _cookie_file_cache is not None:
        if os.path.exists(_cookie_file_cache) and os.path.getsize(_cookie_file_cache) > 10:
            return _cookie_file_cache

    _cookie_file_ts = now

    # Priority: YOUTUBE_COOKIES_B64 env var → file paths
    cookies_b64 = os.environ.get("YOUTUBE_COOKIES_B64", "").strip()
    if cookies_b64:
        tmp_cookies = "/tmp/youtube_cookies.txt"
        try:
            decoded = base64.b64decode(cookies_b64)
            with open(tmp_cookies, "wb") as f:
                f.write(decoded)
            if os.path.getsize(tmp_cookies) > 10:
                _cookie_file_cache = tmp_cookies
                _log.info("[SmartYTDL] Using cookies from YOUTUBE_COOKIES_B64 env var")
                return tmp_cookies
        except Exception as e:
            _log.warning(f"[SmartYTDL] Failed to decode YOUTUBE_COOKIES_B64: {e}")

    for p in _COOKIE_PATHS:
        p = os.path.abspath(p)
        if os.path.exists(p) and os.path.getsize(p) > 10:
            _cookie_file_cache = p
            return p

    _cookie_file_cache = None
    return None


# ── Client registry ─────────────────────────────────────────────────────────────
class _ClientRegistry:
    def __init__(self):
        self._lock = threading.Lock()
        self._best: Optional[str] = "android_embed"
        self._best_ts: float = 0.0
        self._failed: Dict[str, float] = {}
        self._RECHECK_SEC = 900
        self._BEST_TTL_SEC = 1800

    def mark_ok(self, client: str) -> None:
        with self._lock:
            self._best = client
            self._best_ts = time.time()
            self._failed.pop(client, None)

    def mark_failed(self, client: str) -> None:
        with self._lock:
            self._failed[client] = time.time()
            if self._best == client:
                self._best = None

    def get_best(self) -> Optional[str]:
        with self._lock:
            if self._best and (time.time() - self._best_ts) < self._BEST_TTL_SEC:
                return self._best
            return None

    def candidate_clients(self) -> List[str]:
        now = time.time()
        with self._lock:
            best   = self._best
            failed = {c for c, t in self._failed.items() if now - t < self._RECHECK_SEC}
        ordered = []
        if best:
            ordered.append(best)
        for c in ALL_CLIENTS:
            if c not in ordered and c not in failed:
                ordered.append(c)
        for c in ALL_CLIENTS:
            if c not in ordered:
                ordered.append(c)
        return ordered


_registry = _ClientRegistry()


# ── Build yt-dlp options ────────────────────────────────────────────────────────
def _make_opts_for_client(client: str, cookie_file: Optional[str] = None) -> Dict:
    ua = _CLIENT_UA.get(client, _DEFAULT_UA)
    opts: Dict = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "source_address": "0.0.0.0",
        "socket_timeout": 25,
        "retries": 2,
        "extractor_args": {
            "youtube": {
                "player_client": [client],
                "skip": ["hls", "translated_subs"],
            }
        },
        "http_headers": {"User-Agent": ua},
    }
    if cookie_file:
        opts["cookiefile"] = cookie_file
    if _PROXY:
        opts["proxy"] = _PROXY
    return opts


# ── Core extraction/download helpers ───────────────────────────────────────────
def _try_extract_url(vid: str, client: str,
                     cookie_file: Optional[str] = None) -> Optional[Dict]:
    url_str = f"https://www.youtube.com/watch?v={vid}"
    opts = _make_opts_for_client(client, cookie_file)
    opts.update({
        "skip_download": True,
        "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
    })
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url_str, download=False)
        if not info or not info.get("url"):
            return None
        return {
            "url":      info["url"],
            "ext":      info.get("ext", "m4a"),
            "title":    info.get("title", "Unknown"),
            "channel":  info.get("channel") or info.get("uploader", ""),
            "duration": int(info.get("duration") or 0),
            "client":   client,
        }
    except Exception as e:
        _log.debug(f"[SmartYTDL] client={client} extract failed for {vid}: {e}")
        return None


def _try_download(vid: str, client: str, out_dir: str, fmt: str,
                  cookie_file: Optional[str] = None) -> Optional[str]:
    url_str = f"https://www.youtube.com/watch?v={vid}"
    opts = _make_opts_for_client(client, cookie_file)
    opts.update({
        "format":        fmt,
        "outtmpl":       os.path.join(out_dir, f"{vid}.%(ext)s"),
        "noplaylist":    True,
        "overwrites":    True,
        "continuedl":    True,
        "noprogress":    True,
        "socket_timeout": 40,
        "retries":       3,
    })
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.extract_info(url_str, download=True)
        for ext in ("m4a", "webm", "opus", "ogg", "mp3", "mp4"):
            p = os.path.join(out_dir, f"{vid}.{ext}")
            if os.path.exists(p) and os.path.getsize(p) > 1024:
                return p
    except Exception as e:
        _log.debug(f"[SmartYTDL] client={client} download failed for {vid}: {e}")
    return None


# ── Invidious fallback ──────────────────────────────────────────────────────────
def _try_invidious_extract(vid: str) -> Optional[Dict]:
    """
    Try to get stream URL from Invidious public instances.
    Invidious proxies YouTube so it's not subject to the same IP restrictions.
    """
    import urllib.request, json
    for instance in _get_invidious_instances():
        try:
            api_url = f"{instance}/api/v1/videos/{vid}?fields=adaptiveFormats,formatStreams,title,lengthSeconds,author"
            req = urllib.request.Request(api_url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; Annie/2.0)",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status != 200:
                    _mark_invidious_failed(instance)
                    continue
                data = json.loads(resp.read())

            best_url = None
            best_bitrate = 0
            for fmt in data.get("adaptiveFormats", []):
                mime = fmt.get("type", "")
                if "audio" not in mime:
                    continue
                bitrate = int(fmt.get("bitrate", 0))
                if bitrate > best_bitrate:
                    best_bitrate = bitrate
                    best_url = fmt.get("url")

            if not best_url:
                for fmt in data.get("formatStreams", []):
                    best_url = fmt.get("url")
                    break

            if best_url:
                _log.info(f"[SmartYTDL] Invidious SUCCESS via {instance} for {vid}")
                return {
                    "url":      best_url,
                    "ext":      "webm",
                    "title":    data.get("title", "Unknown"),
                    "channel":  data.get("author", ""),
                    "duration": int(data.get("lengthSeconds") or 0),
                    "client":   f"invidious:{instance}",
                }
        except Exception as e:
            _log.debug(f"[SmartYTDL] Invidious {instance} failed for {vid}: {e}")
            _mark_invidious_failed(instance)

    return None


def _try_invidious_download(vid: str, out_dir: str) -> Optional[str]:
    """Download via Invidious — saves the stream URL directly."""
    import urllib.request
    info = _try_invidious_extract(vid)
    if not info:
        return None
    stream_url = info["url"]
    out_path = os.path.join(out_dir, f"{vid}.m4a")
    try:
        req = urllib.request.Request(stream_url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; Annie/2.0)",
            "Referer": "https://www.youtube.com/",
        })
        with urllib.request.urlopen(req, timeout=120) as resp, \
             open(out_path, "wb") as f:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 1024:
            _log.info(f"[SmartYTDL] Invidious download saved: {out_path}")
            return out_path
    except Exception as e:
        _log.debug(f"[SmartYTDL] Invidious download stream failed for {vid}: {e}")
        try:
            os.remove(out_path)
        except Exception:
            pass
    return None


# ── Piped.video API fallback ────────────────────────────────────────────────────
def _try_piped_extract(vid: str) -> Optional[Dict]:
    """
    Try to get stream URL from Piped.video API instances.
    Piped is another YouTube proxy network with different servers.
    """
    import urllib.request, json
    for instance in _get_piped_instances():
        try:
            api_url = f"{instance}/streams/{vid}"
            req = urllib.request.Request(api_url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; Annie/2.0)",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status != 200:
                    _mark_piped_failed(instance)
                    continue
                data = json.loads(resp.read())

            best_url = None
            best_bitrate = 0
            for stream in data.get("audioStreams", []):
                bitrate = int(stream.get("bitrate", 0))
                if bitrate > best_bitrate:
                    best_bitrate = bitrate
                    best_url = stream.get("url")

            if best_url:
                _log.info(f"[SmartYTDL] Piped SUCCESS via {instance} for {vid}")
                return {
                    "url":      best_url,
                    "ext":      "m4a",
                    "title":    data.get("title", "Unknown"),
                    "channel":  data.get("uploader", ""),
                    "duration": int(data.get("duration") or 0),
                    "client":   f"piped:{instance}",
                }
        except Exception as e:
            _log.debug(f"[SmartYTDL] Piped {instance} failed for {vid}: {e}")
            _mark_piped_failed(instance)

    return None


def _try_piped_download(vid: str, out_dir: str) -> Optional[str]:
    """Download via Piped.video API."""
    import urllib.request
    info = _try_piped_extract(vid)
    if not info:
        return None
    stream_url = info["url"]
    out_path = os.path.join(out_dir, f"{vid}.m4a")
    try:
        req = urllib.request.Request(stream_url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; Annie/2.0)",
            "Referer": "https://piped.video/",
        })
        with urllib.request.urlopen(req, timeout=120) as resp, \
             open(out_path, "wb") as f:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 1024:
            _log.info(f"[SmartYTDL] Piped download saved: {out_path}")
            return out_path
    except Exception as e:
        _log.debug(f"[SmartYTDL] Piped download failed for {vid}: {e}")
        try:
            os.remove(out_path)
        except Exception:
            pass
    return None


# ── Public API ──────────────────────────────────────────────────────────────────
def smart_extract_url(vid: str) -> Optional[Dict]:
    """
    Extract a YouTube stream URL.
    Order:
      1. cached best yt-dlp client
      2. all 10 clients in parallel
      3. Invidious fallback (multiple instances)
      4. Piped.video fallback (multiple instances)
    Returns dict with url/ext/title/client, or None if all fail.
    """
    cookie_file = _find_cookie_file()
    if cookie_file:
        _log.info(f"[SmartYTDL] Using cookie file: {cookie_file}")
    if _PROXY:
        _log.info(f"[SmartYTDL] Using proxy: {_PROXY[:30]}...")

    # Fast path: cached best client
    best = _registry.get_best()
    if best:
        result = _try_extract_url(vid, best, cookie_file)
        if result:
            _registry.mark_ok(best)
            return result
        else:
            _log.info(f"[SmartYTDL] Cached client '{best}' failed for {vid}, probing all")
            _registry.mark_failed(best)

    # Parallel probe all clients
    candidates = _registry.candidate_clients()
    results: Dict[str, Optional[Dict]] = {}
    threads = []

    def probe(client):
        results[client] = _try_extract_url(vid, client, cookie_file)

    for client in candidates:
        t = threading.Thread(target=probe, args=(client,), daemon=True)
        threads.append((client, t))
        t.start()

    deadline = time.time() + 30
    for client, t in threads:
        remaining = max(0.1, deadline - time.time())
        t.join(timeout=remaining)
        res = results.get(client)
        if res:
            _registry.mark_ok(client)
            _log.info(f"[SmartYTDL] client='{client}' SUCCESS for {vid}")
            return res
        else:
            _registry.mark_failed(client)

    _log.warning(f"[SmartYTDL] All yt-dlp clients failed for {vid}, trying Invidious")

    # Invidious fallback
    result = _try_invidious_extract(vid)
    if result:
        return result

    # Piped.video fallback
    _log.warning(f"[SmartYTDL] Invidious failed for {vid}, trying Piped.video")
    result = _try_piped_extract(vid)
    if result:
        return result

    _log.error(f"[SmartYTDL] ALL methods failed for {vid}")
    return None


def smart_download(vid: str, out_dir: str,
                   fmt: str = "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best") -> Optional[str]:
    """
    Download YouTube audio.
    Order:
      1. cached best yt-dlp client
      2. all 10 clients sequentially
      3. Invidious download fallback
      4. Piped.video download fallback
    Returns local file path or None.
    """
    cookie_file = _find_cookie_file()

    # Fast path: cached best client
    best = _registry.get_best()
    if best:
        path = _try_download(vid, best, out_dir, fmt, cookie_file)
        if path:
            _registry.mark_ok(best)
            return path
        else:
            _registry.mark_failed(best)

    # Try all clients sequentially
    candidates = _registry.candidate_clients()
    for client in candidates:
        path = _try_download(vid, client, out_dir, fmt, cookie_file)
        if path:
            _registry.mark_ok(client)
            _log.info(f"[SmartYTDL] Download SUCCESS via client='{client}' for {vid}")
            return path
        else:
            _registry.mark_failed(client)

    _log.warning(f"[SmartYTDL] All yt-dlp clients failed for {vid}, trying Invidious download")

    # Invidious download fallback
    path = _try_invidious_download(vid, out_dir)
    if path:
        return path

    # Piped.video download fallback
    _log.warning(f"[SmartYTDL] Invidious failed, trying Piped.video download for {vid}")
    path = _try_piped_download(vid, out_dir)
    if path:
        return path

    _log.error(f"[SmartYTDL] ALL download methods failed for {vid}")
    return None


def get_base_ytdlp_opts(out_dir: str) -> Dict:
    """Base yt-dlp options using best known working client + cookies + proxy if available."""
    best = _registry.get_best() or "android_embed"
    ua = _CLIENT_UA.get(best, _DEFAULT_UA)
    candidates = _registry.candidate_clients()[:3]
    cookie_file = _find_cookie_file()
    opts = {
        "outtmpl":             os.path.join(out_dir, "%(id)s.%(ext)s"),
        "quiet":               True,
        "no_warnings":         True,
        "noplaylist":          True,
        "overwrites":          True,
        "continuedl":          True,
        "noprogress":          True,
        "nocheckcertificate":  True,
        "source_address":      "0.0.0.0",
        "socket_timeout":      30,
        "retries":             3,
        "extractor_args": {
            "youtube": {
                "player_client": candidates,
                "skip": ["hls", "translated_subs"],
            }
        },
        "http_headers": {"User-Agent": ua},
    }
    if cookie_file:
        opts["cookiefile"] = cookie_file
    if _PROXY:
        opts["proxy"] = _PROXY
    return opts


def get_stream_opts() -> Dict:
    """yt-dlp options for URL-only extraction (no download)."""
    best = _registry.get_best() or "android_embed"
    ua = _CLIENT_UA.get(best, _DEFAULT_UA)
    candidates = _registry.candidate_clients()[:3]
    cookie_file = _find_cookie_file()
    opts = {
        "quiet":              True,
        "no_warnings":        True,
        "skip_download":      True,
        "format":             "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
        "nocheckcertificate": True,
        "source_address":     "0.0.0.0",
        "socket_timeout":     20,
        "retries":            3,
        "extractor_args": {
            "youtube": {
                "player_client": candidates,
                "skip": ["hls", "translated_subs"],
            }
        },
        "http_headers": {"User-Agent": ua},
    }
    if cookie_file:
        opts["cookiefile"] = cookie_file
    if _PROXY:
        opts["proxy"] = _PROXY
    return opts


def get_cdn_headers() -> Dict:
    """HTTP headers for CDN URL download."""
    best = _registry.get_best() or "android_embed"
    ua = _CLIENT_UA.get(best, _DEFAULT_UA)
    return {
        "User-Agent": ua,
        "Referer":    "https://www.youtube.com/",
        "Accept":     "*/*",
        "Origin":     "https://www.youtube.com",
    }
