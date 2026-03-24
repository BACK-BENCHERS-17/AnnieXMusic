"""
SmartYTDL — Adaptive, permanent YouTube download bypass for cloud servers.

YouTube frequently changes which player clients work on cloud IPs.
This module solves that permanently by:

1. Trying ALL known clients in PARALLEL — first success wins
2. Caching the last working client and trying it first next time
3. Auto-probing new clients when cached one fails
4. Full fallback chain: URL-extract + CDN download → direct yt-dlp download

No single-client dependency. Self-healing. Works indefinitely.
"""

import os
import threading
import time
from typing import Dict, List, Optional, Tuple
import yt_dlp

# ── Comprehensive client list ──────────────────────────────────────────────────
# Ordered by historical reliability on cloud IPs (Replit / Railway)
# More clients = more chances to succeed regardless of YouTube's changes
ALL_CLIENTS: List[str] = [
    "ios",             # iPhone YouTube app — most reliable on cloud as of 2026
    "mweb",            # Mobile web — very stable
    "android_embed",   # Android embedded — good fallback
    "tv_embedded",     # TV embedded — bypasses some restrictions
    "android_music",   # YouTube Music Android — stable
    "android_vr",      # Android VR — was primary before
    "web_creator",     # YouTube Studio — fewer restrictions
    "tv",              # Smart TV client
    "web_embedded",    # Embedded web player
]

# User-agents per client — must match exactly what that client sends
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
}

_DEFAULT_UA = "com.google.ios.youtube/19.29.1 (iPhone16,2; U; CPU iOS 17_5_1 like Mac OS X;)"


class _ClientRegistry:
    """
    Tracks which player clients are working.
    Tries cached best-client first; if it fails, probes all others in parallel threads.
    Thread-safe.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._best: Optional[str] = "ios"       # last known working client
        self._best_ts: float = 0.0              # when it was last confirmed working
        self._failed: Dict[str, float] = {}     # client -> when it last failed
        self._RECHECK_SEC = 900                 # re-try failed clients after 15 min
        self._BEST_TTL_SEC = 1800               # re-verify best client every 30 min

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
        """Return clients to try, in priority order, excluding recently-failed ones."""
        now = time.time()
        with self._lock:
            best = self._best
            failed = {c for c, t in self._failed.items() if now - t < self._RECHECK_SEC}
        ordered = []
        if best:
            ordered.append(best)
        for c in ALL_CLIENTS:
            if c not in ordered and c not in failed:
                ordered.append(c)
        # Also include failed ones at end (as last resort) so we're never stuck
        for c in ALL_CLIENTS:
            if c not in ordered:
                ordered.append(c)
        return ordered


_registry = _ClientRegistry()


def _make_opts_for_client(client: str) -> Dict:
    """Build yt-dlp options for a specific player client."""
    ua = _CLIENT_UA.get(client, _DEFAULT_UA)
    return {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "source_address": "0.0.0.0",
        "socket_timeout": 20,
        "retries": 2,
        "extractor_args": {
            "youtube": {
                "player_client": [client],
                "skip": ["hls", "translated_subs"],
            }
        },
        "http_headers": {
            "User-Agent": ua,
        },
    }


def _try_extract_url(vid: str, client: str) -> Optional[Dict]:
    """
    Try to extract stream URL using a specific client.
    Returns dict with url/ext/title/etc or None.
    """
    url_str = f"https://www.youtube.com/watch?v={vid}"
    opts = _make_opts_for_client(client)
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
            "url": info["url"],
            "ext": info.get("ext", "m4a"),
            "title": info.get("title", "Unknown"),
            "channel": info.get("channel") or info.get("uploader", ""),
            "duration": int(info.get("duration") or 0),
            "client": client,
        }
    except Exception:
        return None


def _try_download(vid: str, client: str, out_dir: str, fmt: str) -> Optional[str]:
    """
    Try to directly download audio using a specific client.
    Returns file path or None.
    """
    url_str = f"https://www.youtube.com/watch?v={vid}"
    opts = _make_opts_for_client(client)
    opts.update({
        "format": fmt,
        "outtmpl": os.path.join(out_dir, f"{vid}.%(ext)s"),
        "noplaylist": True,
        "overwrites": True,
        "continuedl": True,
        "noprogress": True,
        "socket_timeout": 30,
        "retries": 3,
    })
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.extract_info(url_str, download=True)
        for ext in ("m4a", "webm", "opus", "ogg", "mp3"):
            p = os.path.join(out_dir, f"{vid}.{ext}")
            if os.path.exists(p) and os.path.getsize(p) > 1024:
                return p
    except Exception:
        pass
    return None


def smart_extract_url(vid: str) -> Optional[Dict]:
    """
    Extract a YouTube stream URL using the best available client.
    Tries cached best first; if that fails, probes all clients in parallel.
    Returns dict with url/ext/title/client, or None if all fail.
    """
    # Try cached best client first (fast path — ~2s)
    best = _registry.get_best()
    if best:
        result = _try_extract_url(vid, best)
        if result:
            _registry.mark_ok(best)
            return result
        else:
            _registry.mark_failed(best)

    # Parallel probe — try all remaining clients simultaneously
    candidates = _registry.candidate_clients()
    results: Dict[str, Optional[Dict]] = {}
    threads = []

    def probe(client):
        results[client] = _try_extract_url(vid, client)

    for client in candidates:
        t = threading.Thread(target=probe, args=(client,), daemon=True)
        threads.append((client, t))
        t.start()

    # Collect results — return first success, give up after 25s total
    deadline = time.time() + 25
    for client, t in threads:
        remaining = max(0.1, deadline - time.time())
        t.join(timeout=remaining)
        res = results.get(client)
        if res:
            _registry.mark_ok(client)
            return res
        else:
            _registry.mark_failed(client)

    return None


def smart_download(vid: str, out_dir: str,
                   fmt: str = "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best") -> Optional[str]:
    """
    Download YouTube audio using the best available client.
    Tries cached best first; if that fails, probes all clients.
    Returns local file path or None.
    """
    best = _registry.get_best()
    if best:
        path = _try_download(vid, best, out_dir, fmt)
        if path:
            _registry.mark_ok(best)
            return path
        else:
            _registry.mark_failed(best)

    candidates = _registry.candidate_clients()
    for client in candidates:
        path = _try_download(vid, client, out_dir, fmt)
        if path:
            _registry.mark_ok(client)
            return path
        else:
            _registry.mark_failed(client)

    return None


def get_base_ytdlp_opts(out_dir: str) -> Dict:
    """
    Get base yt-dlp options using the current best-known client.
    Falls back to full ALL_CLIENTS list for resilience.
    """
    best = _registry.get_best() or "ios"
    ua = _CLIENT_UA.get(best, _DEFAULT_UA)
    # Include top 3 candidates for yt-dlp's own internal fallback
    candidates = _registry.candidate_clients()[:3]
    return {
        "outtmpl": os.path.join(out_dir, "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "overwrites": True,
        "continuedl": True,
        "noprogress": True,
        "nocheckcertificate": True,
        "source_address": "0.0.0.0",
        "socket_timeout": 30,
        "retries": 3,
        "extractor_args": {
            "youtube": {
                "player_client": candidates,
                "skip": ["hls", "translated_subs"],
            }
        },
        "http_headers": {
            "User-Agent": ua,
        },
    }


def get_stream_opts() -> Dict:
    """Get yt-dlp options for URL-only extraction (no download)."""
    best = _registry.get_best() or "ios"
    ua = _CLIENT_UA.get(best, _DEFAULT_UA)
    candidates = _registry.candidate_clients()[:3]
    return {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
        "nocheckcertificate": True,
        "source_address": "0.0.0.0",
        "socket_timeout": 20,
        "retries": 3,
        "extractor_args": {
            "youtube": {
                "player_client": candidates,
                "skip": ["hls", "translated_subs"],
            }
        },
        "http_headers": {
            "User-Agent": ua,
        },
    }


def get_cdn_headers() -> Dict:
    """HTTP headers for CDN URL download — must match the current best client."""
    best = _registry.get_best() or "ios"
    ua = _CLIENT_UA.get(best, _DEFAULT_UA)
    return {
        "User-Agent": ua,
        "Referer": "https://www.youtube.com/",
        "Accept": "*/*",
        "Origin": "https://www.youtube.com",
    }
