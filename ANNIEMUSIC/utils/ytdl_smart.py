"""
SmartYTDL — Permanent YouTube bypass using yt-dlp + Node.js JS runtime.

BYPASS LAYERS (tried in order):
  1.  yt-dlp with Node.js js_runtime — solves n-param + signature challenges
  2.  Multiple YouTube player clients raced in PARALLEL
  3.  Invidious public API (fallback, auto-discovers working instances)
  4.  Cookie support — set YOUTUBE_COOKIES_B64 env var (base64 cookies.txt)
  5.  Proxy support  — set YTDL_PROXY env var (socks5://... or http://...)
"""

import base64
import logging
import os
import queue
import random
import shutil
import subprocess
import threading
import time
from typing import Dict, List, Optional
import yt_dlp

_log = logging.getLogger(__name__)

# ── Node.js path detection ───────────────────────────────────────────────────────
def _find_node() -> Optional[str]:
    path = shutil.which("node")
    if path:
        return path
    for p in ["/usr/bin/node", "/usr/local/bin/node", "/opt/homebrew/bin/node"]:
        if os.path.isfile(p):
            return p
    # NixOS paths
    nix_dirs = [d for d in (os.environ.get("PATH", "").split(":")) if "nodejs" in d or "node" in d.lower()]
    for d in nix_dirs:
        candidate = os.path.join(d, "node")
        if os.path.isfile(candidate):
            return candidate
    return None


_NODE_PATH = _find_node()
if _NODE_PATH:
    _log.info(f"[SmartYTDL] Node.js found: {_NODE_PATH}")
else:
    _log.warning("[SmartYTDL] Node.js NOT found — signature solving may fail")


def _js_runtimes() -> Dict:
    if _NODE_PATH:
        return {"node": {"path": _NODE_PATH}}
    return {"node": {}}


# ── Proxy ───────────────────────────────────────────────────────────────────────
_PROXY = (
    os.environ.get("YTDL_PROXY")
    or os.environ.get("HTTPS_PROXY")
    or os.environ.get("HTTP_PROXY")
    or ""
)

# ── YouTube player clients ───────────────────────────────────────────────────────
ALL_CLIENTS: List[str] = [
    "tv",              # Smart TV — reliable with Node.js solver
    "web",             # Desktop web — works with n-param solving
    "tv_embedded",     # TV embedded player
    "web_embedded",    # Embedded web
    "web_creator",     # YouTube Studio — fewer restrictions
    "mweb",            # Mobile web
    "ios",             # iPhone app
]

_CLIENT_UA: Dict[str, str] = {
    "tv":            "Mozilla/5.0 (SMART-TV; Linux; Tizen 6.0) AppleWebKit/538.1 (KHTML, like Gecko) Version/6.0 TV Safari/538.1",
    "web":           "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.118 Safari/537.36",
    "tv_embedded":   "Mozilla/5.0 (SMART-TV; Linux; Tizen 6.0) AppleWebKit/538.1 (KHTML, like Gecko) SamsungBrowser/3.0 TV Safari/538.1",
    "web_embedded":  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.118 Safari/537.36",
    "web_creator":   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.118 Safari/537.36",
    "mweb":          "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "ios":           "com.google.ios.youtube/19.29.1 (iPhone16,2; U; CPU iOS 17_5_1 like Mac OS X;)",
}
_DEFAULT_UA = _CLIENT_UA["tv"]

# ── Invidious instances (fallback pool) ─────────────────────────────────────────
_INVIDIOUS_INSTANCES = [
    "https://invidious.io.lol",
    "https://yewtu.be",
    "https://invidious.fdn.fr",
    "https://inv.ggtyler.dev",
    "https://invidious.perennialte.ch",
    "https://invidious.private.coffee",
    "https://invidious.0011.lt",
    "https://vid.priv.au",
    "https://invidious.darkness.services",
    "https://yt.artemislena.eu",
    "https://invidious.nerdvpn.de",
    "https://invidious.asir.dev",
]

# ── Instance failure tracking ────────────────────────────────────────────────────
_inst_lock = threading.Lock()
_inst_failed: Dict[str, float] = {}
_INST_FAIL_TTL = 600


def _alive_instances(pool: List[str]) -> List[str]:
    now = time.time()
    with _inst_lock:
        good = [i for i in pool if now - _inst_failed.get(i, 0) > _INST_FAIL_TTL]
        bad  = [i for i in pool if i not in good]
    random.shuffle(good)
    return good + bad


def _fail_instance(inst: str):
    with _inst_lock:
        _inst_failed[inst] = time.time()


# ── Cookie support ───────────────────────────────────────────────────────────────
_cookie_cache: Optional[str] = None
_cookie_ts: float = 0.0
_COOKIE_TTL = 120


def _find_cookie_file() -> Optional[str]:
    global _cookie_cache, _cookie_ts
    now = time.time()
    if now - _cookie_ts < _COOKIE_TTL and _cookie_cache:
        if os.path.exists(_cookie_cache) and os.path.getsize(_cookie_cache) > 10:
            return _cookie_cache

    _cookie_ts = now

    # Priority 1: env var (base64 encoded)
    b64 = os.environ.get("YOUTUBE_COOKIES_B64", "").strip()
    if b64:
        tmp = "/tmp/youtube_cookies.txt"
        try:
            with open(tmp, "wb") as f:
                f.write(base64.b64decode(b64))
            if os.path.getsize(tmp) > 10:
                _cookie_cache = tmp
                _log.info("[SmartYTDL] Using cookies from YOUTUBE_COOKIES_B64 env var")
                return tmp
        except Exception as e:
            _log.warning(f"[SmartYTDL] YOUTUBE_COOKIES_B64 decode failed: {e}")

    # Priority 2: local files
    for path in [
        os.path.join(os.path.dirname(__file__), "..", "..", "youtube_cookies.txt"),
        os.path.join(os.path.dirname(__file__), "..", "..", "cookies.txt"),
        "/app/youtube_cookies.txt",
        "/app/cookies.txt",
        "/tmp/youtube_cookies.txt",
    ]:
        p = os.path.abspath(path)
        if os.path.exists(p) and os.path.getsize(p) > 10:
            _cookie_cache = p
            return p

    _cookie_cache = None
    return None


# ── Client registry ──────────────────────────────────────────────────────────────
class _ClientRegistry:
    def __init__(self):
        self._lock = threading.Lock()
        self._best: Optional[str] = "tv"
        self._best_ts: float = 0.0
        self._failed: Dict[str, float] = {}
        self._FAIL_TTL = 900
        self._BEST_TTL = 1800

    def mark_ok(self, client: str):
        with self._lock:
            self._best = client
            self._best_ts = time.time()
            self._failed.pop(client, None)

    def mark_failed(self, client: str):
        with self._lock:
            self._failed[client] = time.time()
            if self._best == client:
                self._best = None

    def get_best(self) -> Optional[str]:
        with self._lock:
            if self._best and time.time() - self._best_ts < self._BEST_TTL:
                return self._best
            return None

    def ordered_clients(self) -> List[str]:
        now = time.time()
        with self._lock:
            best = self._best
            failed = {c for c, t in self._failed.items() if now - t < self._FAIL_TTL}
        result = []
        if best:
            result.append(best)
        for c in ALL_CLIENTS:
            if c not in result and c not in failed:
                result.append(c)
        for c in ALL_CLIENTS:
            if c not in result:
                result.append(c)
        return result


_registry = _ClientRegistry()


# ── yt-dlp option builder ────────────────────────────────────────────────────────
def _opts(client: str, cookie_file: Optional[str] = None) -> Dict:
    ua = _CLIENT_UA.get(client, _DEFAULT_UA)
    o: Dict = {
        "quiet":              True,
        "no_warnings":        True,
        "nocheckcertificate": True,
        "source_address":     "0.0.0.0",
        "socket_timeout":     20,
        "retries":            1,
        "js_runtimes":        _js_runtimes(),
        "extractor_args": {
            "youtube": {
                "player_client": [client],
                "skip": ["hls", "translated_subs"],
            }
        },
        "http_headers": {"User-Agent": ua},
    }
    if cookie_file:
        o["cookiefile"] = cookie_file
    if _PROXY:
        o["proxy"] = _PROXY
    return o


# ── Per-client extract/download ──────────────────────────────────────────────────
_AUDIO_FMT = "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best"


def _client_extract(vid: str, client: str, cookie_file: Optional[str]) -> Optional[Dict]:
    o = _opts(client, cookie_file)
    o.update({"skip_download": True, "format": _AUDIO_FMT})
    try:
        with yt_dlp.YoutubeDL(o) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
        if info and info.get("url"):
            return {
                "url":      info["url"],
                "ext":      info.get("ext", "m4a"),
                "title":    info.get("title", "Unknown"),
                "channel":  info.get("channel") or info.get("uploader", ""),
                "duration": int(info.get("duration") or 0),
                "client":   client,
            }
    except Exception as e:
        _log.debug(f"[SmartYTDL] {client} extract {vid}: {e}")
    return None


def _client_download(vid: str, client: str, out_dir: str,
                     fmt: str, cookie_file: Optional[str]) -> Optional[str]:
    o = _opts(client, cookie_file)
    o.update({
        "format":   fmt,
        "outtmpl":  os.path.join(out_dir, f"{vid}.%(ext)s"),
        "noplaylist": True,
        "overwrites": True,
        "continuedl": True,
        "noprogress": True,
        "socket_timeout": 35,
        "retries": 2,
    })
    try:
        with yt_dlp.YoutubeDL(o) as ydl:
            ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=True)
        for ext in ("m4a", "webm", "opus", "ogg", "mp3", "mp4"):
            p = os.path.join(out_dir, f"{vid}.{ext}")
            if os.path.exists(p) and os.path.getsize(p) > 1024:
                return p
    except Exception as e:
        _log.debug(f"[SmartYTDL] {client} download {vid}: {e}")
    return None


# ── Race helper — first thread to put a result wins ─────────────────────────────
def _race(targets, timeout: float = 22.0) -> Optional[any]:
    result_q: queue.Queue = queue.Queue()
    active = [0]
    lock = threading.Lock()

    def worker(fn):
        try:
            res = fn()
        except Exception:
            res = None
        finally:
            with lock:
                active[0] -= 1
                remaining = active[0]
            if res is not None:
                result_q.put(res)
            elif remaining == 0:
                result_q.put(None)

    with lock:
        active[0] = len(targets)

    threads = []
    for fn in targets:
        t = threading.Thread(target=worker, args=(fn,), daemon=True)
        threads.append(t)
        t.start()

    deadline = time.time() + timeout
    while True:
        remaining_time = max(0.1, deadline - time.time())
        try:
            item = result_q.get(timeout=remaining_time)
            if item is not None:
                return item
            with lock:
                if active[0] == 0:
                    return None
        except queue.Empty:
            return None


# ── Invidious fallback ───────────────────────────────────────────────────────────
def _invidious_extract(vid: str) -> Optional[Dict]:
    import urllib.request, json
    for inst in _alive_instances(_INVIDIOUS_INSTANCES):
        try:
            url = f"{inst}/api/v1/videos/{vid}?fields=adaptiveFormats,formatStreams,title,lengthSeconds,author"
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; Annie/2.0)",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=8) as r:
                if r.status != 200:
                    _fail_instance(inst)
                    continue
                body = r.read()
                if not body or body[:1] not in (b'{', b'['):
                    _fail_instance(inst)
                    continue
                data = json.loads(body)

            best_url, best_br = None, 0
            for fmt in data.get("adaptiveFormats", []):
                if "audio" not in fmt.get("type", ""):
                    continue
                br = int(fmt.get("bitrate", 0))
                if br > best_br:
                    best_br, best_url = br, fmt.get("url")

            if not best_url:
                for fmt in data.get("formatStreams", []):
                    best_url = fmt.get("url")
                    break

            if best_url:
                _log.info(f"[SmartYTDL] Invidious OK {inst} for {vid}")
                return {"url": best_url, "ext": "webm",
                        "title": data.get("title", "Unknown"),
                        "channel": data.get("author", ""),
                        "duration": int(data.get("lengthSeconds") or 0),
                        "client": f"invidious:{inst}"}
        except Exception as e:
            _log.debug(f"[SmartYTDL] Invidious {inst} failed: {e}")
            _fail_instance(inst)
    return None


def _invidious_download(vid: str, out_dir: str) -> Optional[str]:
    import urllib.request
    info = _invidious_extract(vid)
    if not info:
        return None
    out = os.path.join(out_dir, f"{vid}.webm")
    try:
        req = urllib.request.Request(info["url"], headers={
            "User-Agent": "Mozilla/5.0 (compatible; Annie/2.0)",
            "Referer": "https://www.youtube.com/",
        })
        with urllib.request.urlopen(req, timeout=90) as r, open(out, "wb") as f:
            while True:
                chunk = r.read(65536)
                if not chunk:
                    break
                f.write(chunk)
        if os.path.exists(out) and os.path.getsize(out) > 1024:
            _log.info(f"[SmartYTDL] Invidious download ok: {out}")
            return out
    except Exception as e:
        _log.debug(f"[SmartYTDL] Invidious stream download failed: {e}")
    try:
        os.remove(out)
    except Exception:
        pass
    return None


# ── Public API ───────────────────────────────────────────────────────────────────
def smart_extract_url(vid: str) -> Optional[Dict]:
    """
    Extract YouTube stream URL.
    Uses Node.js js_runtime for signature/n-param solving.
    Falls back to Invidious if yt-dlp fails.
    """
    cookie_file = _find_cookie_file()
    if cookie_file:
        _log.info(f"[SmartYTDL] Using cookie file: {cookie_file}")

    # Fast path — cached best client
    best = _registry.get_best()
    if best:
        res = _client_extract(vid, best, cookie_file)
        if res:
            _registry.mark_ok(best)
            return res
        _registry.mark_failed(best)
        _log.info(f"[SmartYTDL] Cached '{best}' failed for {vid}, racing all")

    # Race all clients in parallel — first success wins
    clients = _registry.ordered_clients()
    _log.info(f"[SmartYTDL] Racing {len(clients)} clients for {vid}")

    targets = [
        (lambda c: lambda: _client_extract(vid, c, cookie_file))(c)
        for c in clients
    ]
    winner = _race(targets, timeout=30.0)

    if winner:
        _registry.mark_ok(winner["client"])
        _log.info(f"[SmartYTDL] client='{winner['client']}' won for {vid}")
        return winner

    # Invidious fallback
    _log.warning(f"[SmartYTDL] All yt-dlp clients failed for {vid} → Invidious")
    res = _invidious_extract(vid)
    if res:
        return res

    _log.error(f"[SmartYTDL] ALL extract methods failed for {vid}")
    return None


def smart_download(vid: str, out_dir: str,
                   fmt: str = _AUDIO_FMT) -> Optional[str]:
    """
    Download YouTube audio.
    Tries cached best client first, then races all clients, then Invidious.
    """
    cookie_file = _find_cookie_file()

    # Fast path — cached best client
    best = _registry.get_best()
    if best:
        p = _client_download(vid, best, out_dir, fmt, cookie_file)
        if p:
            _registry.mark_ok(best)
            return p
        _registry.mark_failed(best)

    # Race all clients
    clients = _registry.ordered_clients()
    targets = [
        (lambda c: lambda: _client_download(vid, c, out_dir, fmt, cookie_file))(c)
        for c in clients
    ]
    winner_path = _race(targets, timeout=60.0)
    if winner_path:
        _log.info(f"[SmartYTDL] Download won for {vid}: {winner_path}")
        return winner_path

    # Invidious fallback
    _log.warning(f"[SmartYTDL] All yt-dlp clients failed download for {vid} → Invidious")
    p = _invidious_download(vid, out_dir)
    if p:
        return p

    _log.error(f"[SmartYTDL] ALL download methods failed for {vid}")
    return None


# ── Helpers used by the rest of the codebase ────────────────────────────────────
def get_base_ytdlp_opts(out_dir: str) -> Dict:
    best = _registry.get_best() or "tv"
    ua = _CLIENT_UA.get(best, _DEFAULT_UA)
    candidates = _registry.ordered_clients()[:3]
    cookie_file = _find_cookie_file()
    o = {
        "outtmpl":            os.path.join(out_dir, "%(id)s.%(ext)s"),
        "quiet":              True,
        "no_warnings":        True,
        "noplaylist":         True,
        "overwrites":         True,
        "continuedl":         True,
        "noprogress":         True,
        "nocheckcertificate": True,
        "source_address":     "0.0.0.0",
        "socket_timeout":     30,
        "retries":            3,
        "js_runtimes":        _js_runtimes(),
        "extractor_args": {
            "youtube": {
                "player_client": candidates,
                "skip": ["hls", "translated_subs"],
            }
        },
        "http_headers": {"User-Agent": ua},
    }
    if cookie_file:
        o["cookiefile"] = cookie_file
    if _PROXY:
        o["proxy"] = _PROXY
    return o


def get_cdn_headers() -> Dict:
    """Return HTTP headers suitable for downloading from a YouTube CDN URL."""
    best = _registry.get_best() or "tv"
    ua = _CLIENT_UA.get(best, _DEFAULT_UA)
    return {
        "User-Agent": ua,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.youtube.com/",
        "Origin": "https://www.youtube.com",
    }


def get_stream_opts() -> Dict:
    best = _registry.get_best() or "tv"
    ua = _CLIENT_UA.get(best, _DEFAULT_UA)
    candidates = _registry.ordered_clients()[:3]
    cookie_file = _find_cookie_file()
    o = {
        "quiet":              True,
        "no_warnings":        True,
        "skip_download":      True,
        "format":             _AUDIO_FMT,
        "nocheckcertificate": True,
        "source_address":     "0.0.0.0",
        "socket_timeout":     20,
        "retries":            2,
        "js_runtimes":        _js_runtimes(),
        "extractor_args": {
            "youtube": {
                "player_client": candidates,
                "skip": ["hls", "translated_subs"],
            }
        },
        "http_headers": {"User-Agent": ua},
    }
    if cookie_file:
        o["cookiefile"] = cookie_file
    if _PROXY:
        o["proxy"] = _PROXY
    return o
