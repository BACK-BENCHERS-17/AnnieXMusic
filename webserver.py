import os
import time
import threading
import sys
import psutil
import yt_dlp
from flask import Flask, jsonify, send_from_directory, request, Response, send_file
import requests
import re
from urllib.parse import urlparse, parse_qs

# ── SmartYTDL import (add repo root to path if needed) ───────────────────────
_repo_root = os.path.dirname(os.path.abspath(__file__))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)
from ANNIEMUSIC.utils.ytdl_smart import smart_extract_url, smart_download, get_stream_opts, get_cdn_headers
from ANNIEMUSIC.utils.internal_secret import get_secret

_INTERNAL_KEY = get_secret()   # random per-process, never logged
_DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(_DOWNLOAD_DIR, exist_ok=True)
_ytdl_locks: dict = {}
_ytdl_lock_guard = threading.Lock()

# ── Local audio file cache ────────────────────────────────────────────────────
_local_file_cache: dict = {}
_local_file_lock = threading.Lock()
_local_dl_locks: dict = {}
_local_dl_lock_guard = threading.Lock()

WEB_DIR = os.path.join(os.path.dirname(__file__), 'ANNIEMUSIC', 'utils', 'web')
app = Flask(__name__)
_boot_time = time.time()

# ── CORS — allow anyone to call these APIs from any bot/server ────────────────
try:
    from flask_cors import CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
except Exception:
    @app.after_request
    def _add_cors(response):
        response.headers["Access-Control-Allow-Origin"]  = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

def _sec_to_min(s):
    if not s:
        return "0:00"
    s = int(s)
    return f"{s // 60}:{s % 60:02d}"

# ── Stream cache ─────────────────────────────────────────────────────────────
_stream_cache = {}
_stream_lock  = threading.Lock()

def _is_url_valid(data):
    try:
        exp = parse_qs(urlparse(data.get("url", "")).query).get("expire", [None])[0]
        if exp:
            return time.time() < int(exp) - 300
    except Exception:
        pass
    return time.time() - data.get("ts", 0) < 3600

def _fetch_stream_url(vid):
    """
    Fetch YouTube audio stream URL using SmartYTDL.
    Tries the cached best client first, then probes all clients in parallel.
    Permanently adapts to YouTube's anti-bot changes.
    """
    info = smart_extract_url(vid)
    if not info:
        return None
    dur = info.get("duration", 0)
    return {
        "url":      info["url"],
        "ext":      info.get("ext", "m4a"),
        "title":    info.get("title", "Unknown"),
        "channel":  info.get("channel", ""),
        "duration": _sec_to_min(dur),
        "seconds":  dur,
        "thumb":    f"https://img.youtube.com/vi/{vid}/mqdefault.jpg",
        "ts":       time.time(),
    }

def _fetch_stream_with_cookies(vid):
    return _fetch_stream_url(vid)

def _download_audio_local(vid):
    """
    Download audio to disk using SmartYTDL.
    Tries cached best client first, then probes all clients if needed.
    Thread-safe with per-video locking.
    """
    with _local_file_lock:
        cached = _local_file_cache.get(vid)
    if cached and os.path.exists(cached):
        return cached

    with _local_dl_lock_guard:
        if vid not in _local_dl_locks:
            _local_dl_locks[vid] = threading.Lock()
        vid_lock = _local_dl_locks[vid]

    with vid_lock:
        with _local_file_lock:
            cached = _local_file_cache.get(vid)
        if cached and os.path.exists(cached):
            return cached

        fmt = "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best"
        path = smart_download(vid, _DOWNLOAD_DIR, fmt)
        if path:
            with _local_file_lock:
                _local_file_cache[vid] = path
            return path
    return None

def _get_stream_data(vid, force_refresh=False):
    if not force_refresh:
        with _stream_lock:
            cached = _stream_cache.get(vid)
        if cached and _is_url_valid(cached):
            return cached
    data = _fetch_stream_with_cookies(vid)
    if data:
        with _stream_lock:
            _stream_cache[vid] = data
    return data

# ── Trending cache ───────────────────────────────────────────────────────────
_trending_cache = {"data": [], "ts": 0}
_CACHE_TTL = 1800  # 30 min

TRENDING_QUERIES = [
    ("Hindi", [
        "ytsearch30:new hindi song 2025",
        "ytsearch20:hindi latest song 2025",
    ]),
    ("Punjabi", [
        "ytsearch30:new punjabi song 2025",
        "ytsearch20:punjabi latest song 2025",
    ]),
    ("Bollywood", [
        "ytsearch30:bollywood new song 2025",
        "ytsearch20:bollywood hit song 2025",
    ]),
    ("International", [
        "ytsearch30:new english song 2025",
        "ytsearch20:top pop song 2025",
    ]),
]

# Keywords that identify non-individual songs (compilations/jukeboxes/playlists)
_SKIP_KEYWORDS = {
    "jukebox", "playlist", "non stop", "nonstop", "mashup",
    "part 1", "part 2", "part-1", "part-2", "vol.", "vol ",
    "top 10", "top 20", "top 50", "top 100",
    "best of", "hits of", "collection", "compilation",
    "audio jukebox", "video jukebox", "full album", "all songs",
    "back to back", "back2back", "evergreen", "jhankar",
}
_MAX_DURATION_SEC = 600   # 10 minutes — individual songs
_MIN_DURATION_SEC = 60    # 1 minute  — skip short clips

def _is_individual_song(title: str, duration_sec: int) -> bool:
    """Return True if this looks like an individual song (not a compilation)."""
    tl = title.lower()
    for kw in _SKIP_KEYWORDS:
        if kw in tl:
            return False
    return _MIN_DURATION_SEC <= duration_sec <= _MAX_DURATION_SEC

def _fetch_trending():
    seen_ids = set()
    short_results = []   # individual songs ≤ 10 min
    long_results  = []   # longer / unfiltered fallback

    ydl_opts = {
        "quiet": True, "no_warnings": True,
        "extract_flat": True, "skip_download": True,
        "ignoreerrors": True,
    }

    for category, queries in TRENDING_QUERIES:
        for query in queries:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(query, download=False)
                    entries = info.get("entries", []) if info else []
                    for e in (entries or []):
                        if not e:
                            continue
                        vid = e.get("id") or ""
                        if not vid or len(vid) != 11 or vid in seen_ids:
                            continue
                        seen_ids.add(vid)
                        title   = e.get("title", "Unknown")
                        dur_sec = int(e.get("duration") or 0)
                        dur_str = e.get("duration_string") or _sec_to_min(dur_sec)
                        entry = {
                            "id":       vid,
                            "title":    title,
                            "channel":  e.get("channel") or e.get("uploader", ""),
                            "duration": dur_str,
                            "thumb":    f"https://img.youtube.com/vi/{vid}/mqdefault.jpg",
                            "category": category,
                        }
                        if _is_individual_song(title, dur_sec):
                            short_results.append(entry)
                        else:
                            long_results.append(entry)
            except Exception:
                pass

    # Prefer short/individual songs; use long ones only as backfill
    combined = short_results
    if len(combined) < 40:
        combined = combined + long_results
    return combined

def get_trending():
    now = time.time()
    if now - _trending_cache["ts"] > _CACHE_TTL or not _trending_cache["data"]:
        try:
            data = _fetch_trending()
            if data:
                _trending_cache["data"] = data
                _trending_cache["ts"] = now
        except Exception:
            pass
    return _trending_cache["data"]

# Start trending prefetch in background on startup
threading.Thread(target=get_trending, daemon=True).start()

# ── Routes ──────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")

@app.route("/api/status")
def api_status():
    try:
        from ANNIEMUSIC.misc import db, _boot_
        boot_time = _boot_
    except Exception:
        db = {}
        boot_time = _boot_time

    chats_data = []
    for chat_id, queue in db.items():
        if not queue:
            continue
        cur = queue[0]
        vid = str(cur.get("vidid", ""))
        thumb = f"https://img.youtube.com/vi/{vid}/mqdefault.jpg" if len(vid) == 11 else ""
        user_id = cur.get("user_id", 0)
        chats_data.append({
            "chat_id": chat_id,
            "current": {
                "title":      cur.get("title", "Unknown"),
                "duration":   cur.get("dur", "0:00"),
                "played":     cur.get("played", 0),
                "seconds":    cur.get("seconds", 0),
                "by":         cur.get("by", "Unknown"),
                "user_id":    user_id,
                "tg_link":    f"tg://user?id={user_id}" if user_id else "",
                "streamtype": cur.get("streamtype", "youtube"),
                "vidid":      vid,
                "thumbnail":  thumb,
            },
            "queue_count": max(len(queue) - 1, 0),
            "queue": [
                {
                    "title":    t.get("title", "Unknown"),
                    "duration": t.get("dur", "0:00"),
                    "by":       t.get("by", "Unknown"),
                    "vidid":    str(t.get("vidid", "")),
                    "thumb":    f"https://img.youtube.com/vi/{str(t.get('vidid',''))}/default.jpg"
                                if len(str(t.get("vidid", ""))) == 11 else "",
                }
                for t in queue[1:8]
            ],
        })

    try:
        cpu     = psutil.cpu_percent(interval=None)
        ram     = psutil.virtual_memory()
        ram_used  = f"{ram.used // (1024**2)} MB"
        ram_total = f"{ram.total // (1024**2)} MB"
        ram_pct   = round(ram.percent, 1)
    except Exception:
        cpu, ram_used, ram_total, ram_pct = 0, "N/A", "N/A", 0

    up   = int(time.time() - boot_time)
    h, rem = divmod(up, 3600)
    m, s   = divmod(rem, 60)

    return jsonify({
        "status":       "online",
        "uptime":       f"{h}h {m}m {s}s",
        "active_chats": len(chats_data),
        "cpu":          cpu,
        "ram_used":     ram_used,
        "ram_total":    ram_total,
        "ram_percent":  ram_pct,
        "chats":        chats_data,
    })

@app.route("/api/trending")
def api_trending():
    data = get_trending()
    return jsonify({"songs": data, "cached": bool(data)})

@app.route("/api/yturl")
def api_yturl():
    """
    Internal API: return actual stream URL for bot use.
    Protected by internal random key — only the bot (same Railway service) can call this.
    GET /api/yturl?v=VIDEO_ID&key=INTERNAL_KEY
    """
    vid = request.args.get("v", "").strip()
    key = request.args.get("key", "").strip()

    if not vid or len(vid) != 11:
        return jsonify({"error": "Invalid video id"}), 400

    if key != _INTERNAL_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data = _get_stream_data(vid)
        if not data or not data.get("url"):
            return jsonify({"error": "Could not fetch stream URL"}), 500
        return jsonify({
            "url":      data["url"],
            "ext":      data.get("ext", "m4a"),
            "title":    data["title"],
            "channel":  data["channel"],
            "duration": data["duration"],
            "seconds":  data["seconds"],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _file_exists_any(vid):
    """Return path if any audio file exists for this video id."""
    for ext in ("m4a", "mp3", "webm", "opus", "ogg", "flac"):
        p = os.path.join(_DOWNLOAD_DIR, f"{vid}.{ext}")
        if os.path.exists(p) and os.path.getsize(p) > 1024:
            return p
    return None


def _cdn_download_sync(vid, stream_url, ext):
    """Synchronously download audio from CDN URL. Returns file path or None."""
    out_path = os.path.join(_DOWNLOAD_DIR, f"{vid}.{ext}")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 1024:
        return out_path
    tmp_path = out_path + ".tmp"
    try:
        headers = get_cdn_headers()
        with requests.get(stream_url, headers=headers, stream=True, timeout=90) as resp:
            if resp.status_code not in (200, 206):
                return None
            with open(tmp_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 1024:
            os.replace(tmp_path, out_path)
            return out_path
    except Exception as e:
        try:
            os.remove(tmp_path)
        except Exception:
            pass
    return None


@app.route("/api/ytdl")
def api_ytdl():
    """
    Internal API: download YouTube audio to local file (fast path first).
    Protected by internal random key — only the bot (same process) should call this.
    GET /api/ytdl?v=VIDEO_ID&key=INTERNAL_KEY
    Returns: {"path": "/abs/path/to/VIDEO_ID.<ext>"}

    Fast path: smart_extract_url → CDN download (no ffmpeg, ~1-3s)
    Slow path: yt-dlp full download + ffmpeg MP3 (fallback only)
    """
    vid = request.args.get("v", "").strip()
    key = request.args.get("key", "").strip()

    if not vid or len(vid) != 11:
        return jsonify({"error": "Invalid video id"}), 400
    if key != _INTERNAL_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    # ── Check any existing file first ────────────────────────────────────────
    existing = _file_exists_any(vid)
    if existing:
        return jsonify({"path": existing, "cached": True})

    with _ytdl_lock_guard:
        if vid not in _ytdl_locks:
            _ytdl_locks[vid] = threading.Lock()
        vid_lock = _ytdl_locks[vid]

    with vid_lock:
        existing = _file_exists_any(vid)
        if existing:
            return jsonify({"path": existing, "cached": True})

        # ── Fast path: stream URL → CDN download (no ffmpeg needed) ─────────
        try:
            stream_data = _get_stream_data(vid)
            if stream_data and stream_data.get("url"):
                ext = stream_data.get("ext", "m4a")
                path = _cdn_download_sync(vid, stream_data["url"], ext)
                if path:
                    return jsonify({"path": path, "method": "cdn"})
        except Exception as e:
            pass  # fall through to slow path

        # ── Slow path: yt-dlp + ffmpeg MP3 (fallback) ───────────────────────
        out_path = os.path.join(_DOWNLOAD_DIR, f"{vid}.mp3")
        tmp_path = out_path + ".tmp"
        opts = {
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }],
            "outtmpl": os.path.join(_DOWNLOAD_DIR, f"{vid}.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["tv", "web_embedded", "web_creator", "android_vr"],
                    "skip": ["hls", "translated_subs"],
                }
            },
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (SMART-TV; Linux; Tizen 6.0) AppleWebKit/538.1 (KHTML, like Gecko) Version/6.0 TV Safari/538.1",
            },
            "socket_timeout": 30,
            "retries": 3,
            "nocheckcertificate": True,
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=True)
            existing = _file_exists_any(vid)
            if existing:
                return jsonify({"path": existing, "method": "ytdlp"})
            return jsonify({"error": "Download produced no file"}), 500
        except Exception as e:
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            return jsonify({"error": str(e)}), 500
        finally:
            with _ytdl_lock_guard:
                _ytdl_locks.pop(vid, None)


@app.route("/api/stream")
def api_stream():
    """Return metadata for a video (no stream URL exposed to browser)."""
    vid = request.args.get("v", "").strip()
    if not vid or len(vid) != 11:
        return jsonify({"error": "Invalid video id"}), 400
    try:
        data = _get_stream_data(vid)
        if data:
            return jsonify({
                "title":    data["title"],
                "channel":  data["channel"],
                "duration": data["duration"],
                "seconds":  data["seconds"],
                "thumb":    data["thumb"],
            })
        # Fallback: use YouTube oEmbed (no bot detection, gives title + thumb)
        try:
            oe = requests.get(
                f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid}&format=json",
                timeout=8,
            ).json()
            return jsonify({
                "title":    oe.get("title", vid),
                "channel":  oe.get("author_name", ""),
                "duration": "0:00",
                "seconds":  0,
                "thumb":    f"https://img.youtube.com/vi/{vid}/mqdefault.jpg",
            })
        except Exception:
            pass
        return jsonify({"error": "Could not fetch stream"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def _proxy_audio(vid, force_refresh=False):
    """
    Fetch stream data and proxy audio from YouTube.
    Returns a Flask Response, or raises an exception.
    If force_refresh=True, bypass cache and fetch a fresh URL.
    Uses client-matched headers to reduce CDN 403 errors.
    """
    data = _get_stream_data(vid, force_refresh=force_refresh)
    if not data:
        return None, None

    stream_url = data["url"]
    ext = data.get("ext", "m4a")
    content_type = "audio/mp4" if ext == "m4a" else f"audio/{ext}"

    range_header = request.headers.get("Range")
    # Use SmartYTDL matched headers — reduces CDN 403 rate
    req_headers = dict(get_cdn_headers())
    req_headers["Accept-Encoding"] = "identity"
    req_headers["Connection"] = "keep-alive"
    if range_header:
        req_headers["Range"] = range_header

    upstream = requests.get(stream_url, headers=req_headers, stream=True, timeout=30)
    return upstream, content_type


def _check_bot_downloads(vid: str):
    """Check bot's download directory for a cached audio file."""
    bot_dl_dir = os.path.join(os.path.dirname(__file__), "downloads")
    for ext in ("m4a", "mp3", "webm", "opus", "ogg", "flac", "mp4"):
        p = os.path.join(bot_dl_dir, f"{vid}.{ext}")
        if os.path.exists(p) and os.path.getsize(p) > 1024:
            return p
    return None


@app.route("/api/audio")
def api_audio():
    """Proxy audio stream from YouTube — avoids browser CORS issues."""
    vid = request.args.get("v", "").strip()
    if not vid or len(vid) != 11:
        return jsonify({"error": "Invalid video id"}), 400
    try:
        # ── Fast path: serve from bot's download cache (already on disk) ────
        cached = _check_bot_downloads(vid)
        if cached:
            ext = os.path.splitext(cached)[1].lstrip(".")
            mime = "audio/mp4" if ext == "m4a" else f"audio/{ext}"
            return send_file(cached, mimetype=mime, conditional=True)

        # ── Try CDN proxy ────────────────────────────────────────────────────
        upstream, content_type = _proxy_audio(vid, force_refresh=False)

        # If stream URL extraction failed or YouTube rejected URL, try refresh once
        if upstream is not None and upstream.status_code in (400, 403, 410):
            upstream.close()
            upstream, content_type = _proxy_audio(vid, force_refresh=True)

        # If stream URL proxy works, serve it directly
        if upstream is not None and upstream.status_code not in (400, 403, 410, 500):
            resp_headers = {
                "Content-Type":  upstream.headers.get("Content-Type", content_type),
                "Accept-Ranges": "bytes",
                "Cache-Control": "no-cache",
            }
            if "Content-Length" in upstream.headers:
                resp_headers["Content-Length"] = upstream.headers["Content-Length"]
            if "Content-Range" in upstream.headers:
                resp_headers["Content-Range"] = upstream.headers["Content-Range"]
            status_code = upstream.status_code
            def generate():
                for chunk in upstream.iter_content(chunk_size=65536):
                    if chunk:
                        yield chunk
            return Response(generate(), status=status_code, headers=resp_headers)

        # ── Fallback: download audio locally and serve from disk ─────────────
        # (handles cloud IPs blocked by YouTube — client headers now match URL client)
        if upstream is not None:
            try:
                upstream.close()
            except Exception:
                pass
        file_path = _download_audio_local(vid)
        if file_path is None:
            # Last chance: check bot downloads again (might have been added during above)
            file_path = _check_bot_downloads(vid)
        if file_path is None:
            return jsonify({"error": "Could not fetch audio"}), 503
        ext = os.path.splitext(file_path)[1].lstrip(".")
        mime = "audio/mp4" if ext == "m4a" else f"audio/{ext}"
        return send_file(file_path, mimetype=mime, conditional=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/related")
def api_related():
    """Return related songs for a given video ID (used for web autoplay)."""
    vid = request.args.get("v", "").strip()
    if not vid or len(vid) != 11:
        return jsonify({"results": []}), 400
    try:
        # Get current song info first for a smarter query
        with _stream_lock:
            cached = _stream_cache.get(vid)
        title = cached.get("title", "") if cached else ""
        words = [w for w in title.split() if len(w) > 3] if title else []
        base = words[0] if words else "hindi songs"
        import random
        suffixes = ["best songs", "hit songs", "top songs", "playlist", "popular songs", "superhit songs"]
        query = f"{base} {random.choice(suffixes)} 2025"

        ydl_opts = {
            "quiet": True, "no_warnings": True,
            "extract_flat": True, "skip_download": True,
            "ignoreerrors": True,
        }
        short_r, long_r = [], []
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch20:{query}", download=False)
            entries = info.get("entries", []) if info else []
            for e in (entries or []):
                if not e:
                    continue
                eid = e.get("id") or ""
                if not eid or len(eid) != 11 or eid == vid:
                    continue
                etitle  = e.get("title", "Unknown")
                edur    = int(e.get("duration") or 0)
                edur_s  = e.get("duration_string") or _sec_to_min(edur)
                entry = {
                    "id":       eid,
                    "title":    etitle,
                    "channel":  e.get("channel") or e.get("uploader", ""),
                    "duration": edur_s,
                    "thumb":    f"https://img.youtube.com/vi/{eid}/mqdefault.jpg",
                }
                if _is_individual_song(etitle, edur):
                    short_r.append(entry)
                else:
                    long_r.append(entry)
        results = short_r if short_r else long_r
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"results": [], "error": str(e)}), 500

_INVIDIOUS_INSTANCES = [
    "https://invidious.nerdvpn.de",
    "https://inv.nadeko.net",
    "https://invidious.privacyredirect.com",
    "https://yt.cdaut.de",
    "https://invidious.flokinet.to",
    "https://invidious.perennialte.ch",
    "https://iv.datura.network",
    "https://invidious.protokolla.fi",
    "https://invidious.fdn.fr",
    "https://invidious.einfachzocken.eu",
]
_inv_health = {}
_COOLDOWN_SEC = 120


def _get_healthy_instances():
    import random
    now = time.time()
    ok = [i for i in _INVIDIOUS_INSTANCES if now - _inv_health.get(i, 0) > _COOLDOWN_SEC]
    if not ok:
        _inv_health.clear()
        ok = list(_INVIDIOUS_INSTANCES)
    random.shuffle(ok)
    return ok


def _search_via_ytapi(q: str, max_results: int = 15):
    """
    Permanent free YouTube search:
    1. Invidious API (free, unlimited, no key needed) — primary
    2. YouTube Data API v3 (only if YOUTUBE_API_KEY set) — optional
    Returns None if both fail (falls through to yt-dlp).
    """
    import urllib.request
    import urllib.parse
    import json as _json

    search_params = urllib.parse.urlencode({
        "q": q,
        "type": "video",
        "fields": "videoId,title,author,lengthSeconds,videoThumbnails",
    })

    for instance in _get_healthy_instances()[:5]:
        try:
            url = f"{instance}/api/v1/search?{search_params}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                data = _json.loads(r.read())
            if not data or not isinstance(data, list):
                _inv_health[instance] = time.time()
                continue
            results = []
            for item in data[:max_results]:
                vid = item.get("videoId", "")
                if not vid:
                    continue
                secs = int(item.get("lengthSeconds") or 0)
                thumbs = item.get("videoThumbnails") or []
                thumb = next(
                    (t["url"] for t in thumbs if t.get("quality") == "medium"),
                    next((t["url"] for t in thumbs if t.get("url")),
                         f"https://img.youtube.com/vi/{vid}/mqdefault.jpg")
                )
                if thumb and thumb.startswith("/vi/"):
                    thumb = f"https://img.youtube.com{thumb}"
                results.append({
                    "id":       vid,
                    "title":    item.get("title", "Unknown"),
                    "channel":  item.get("author", ""),
                    "duration": _sec_to_min(secs),
                    "thumb":    thumb,
                })
            if results:
                return results
        except Exception:
            _inv_health[instance] = time.time()
            continue

    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        def iso_to_sec(d):
            import re as _re
            m = _re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
            if not m:
                return 0
            return int(m.group(1) or 0)*3600 + int(m.group(2) or 0)*60 + int(m.group(3) or 0)

        sp = urllib.parse.urlencode({"key": api_key, "q": q, "part": "snippet",
                                     "type": "video", "maxResults": min(max_results, 50)})
        with urllib.request.urlopen(
            f"https://www.googleapis.com/youtube/v3/search?{sp}", timeout=6
        ) as r:
            sdata = _json.loads(r.read())

        items = sdata.get("items", [])
        vids = [i["id"]["videoId"] for i in items if i.get("id", {}).get("videoId")]
        if not vids:
            return None

        dp = urllib.parse.urlencode({"key": api_key, "id": ",".join(vids), "part": "contentDetails"})
        with urllib.request.urlopen(
            f"https://www.googleapis.com/youtube/v3/videos?{dp}", timeout=6
        ) as r:
            ddata = _json.loads(r.read())
        dmap = {v["id"]: iso_to_sec(v.get("contentDetails", {}).get("duration", ""))
                for v in ddata.get("items", [])}

        results = []
        for item in items:
            vid = item.get("id", {}).get("videoId", "")
            if not vid:
                continue
            snippet = item.get("snippet", {})
            secs = dmap.get(vid, 0)
            results.append({
                "id":       vid,
                "title":    snippet.get("title", "Unknown"),
                "channel":  snippet.get("channelTitle", ""),
                "duration": _sec_to_min(secs),
                "thumb":    (snippet.get("thumbnails", {}).get("medium", {}).get("url")
                             or f"https://img.youtube.com/vi/{vid}/mqdefault.jpg"),
            })
        return results or None
    except Exception:
        return None


@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"results": []})
    try:
        api_results = _search_via_ytapi(q, max_results=15)
        if api_results is not None:
            return jsonify({"results": api_results, "source": "invidious_free"})

        ydl_opts = {
            "quiet": True, "no_warnings": True,
            "extract_flat": True, "skip_download": True,
            "ignoreerrors": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch15:{q}", download=False)
            entries = info.get("entries", []) if info else []
            results = []
            for e in (entries or []):
                if not e:
                    continue
                vid = e.get("id") or ""
                if not vid or len(vid) != 11:
                    continue
                results.append({
                    "id":       vid,
                    "title":    e.get("title", "Unknown"),
                    "channel":  e.get("channel") or e.get("uploader", ""),
                    "duration": e.get("duration_string") or _sec_to_min(e.get("duration", 0)),
                    "thumb":    f"https://img.youtube.com/vi/{vid}/mqdefault.jpg",
                })
        return jsonify({"results": results, "source": "ytdlp"})
    except Exception as e:
        return jsonify({"error": str(e), "results": []}), 500

@app.route("/api/download")
def api_download():
    """Download audio by proxying stream with Content-Disposition (fast, no temp file)."""
    vid = request.args.get("v", "").strip()
    if not vid or len(vid) != 11:
        return jsonify({"error": "Invalid video id"}), 400
    try:
        data = _get_stream_data(vid)
        if not data or not data.get("url"):
            return jsonify({"error": "Could not fetch stream"}), 500

        stream_url = data["url"]
        ext = data.get("ext", "m4a")
        title = data.get("title", vid)
        safe_title = re.sub(r'[^\w\s\-\.]', '_', title)[:80].strip()
        filename = f"{safe_title}.{ext}"
        mime = "audio/mp4" if ext in ("m4a", "mp4") else f"audio/{ext}"

        req_headers = {
            "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept":          "*/*",
            "Accept-Encoding": "identity",
            "Connection":      "keep-alive",
            "Referer":         "https://www.youtube.com/",
        }
        upstream = requests.get(stream_url, headers=req_headers, stream=True, timeout=30)

        # If expired, refresh once
        if upstream.status_code in (400, 403, 410):
            upstream.close()
            data = _get_stream_data(vid, force_refresh=True)
            if not data or not data.get("url"):
                return jsonify({"error": "Could not refresh stream"}), 500
            stream_url = data["url"]
            upstream = requests.get(stream_url, headers=req_headers, stream=True, timeout=30)

        resp_headers = {
            "Content-Type":        upstream.headers.get("Content-Type", mime),
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control":       "no-cache",
        }
        if "Content-Length" in upstream.headers:
            resp_headers["Content-Length"] = upstream.headers["Content-Length"]

        def generate():
            for chunk in upstream.iter_content(chunk_size=65536):
                if chunk:
                    yield chunk

        return Response(generate(), status=200, headers=resp_headers)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/botinfo")
def api_botinfo():
    """Return bot profile info."""
    try:
        from config import BOT_NAME, BOT_USERNAME
    except Exception:
        BOT_NAME = "Annie X Music"
        BOT_USERNAME = "ANNIEXMUSICxBOT"
    has_pfp = os.path.isfile("ANNIEMUSIC/assets/bot_pfp.png")
    has_upic = os.path.isfile("ANNIEMUSIC/assets/upic.png")
    pfp_url = "/api/botpfp" if (has_pfp or has_upic) else None
    return jsonify({
        "name":     BOT_NAME,
        "username": BOT_USERNAME,
        "pfp":      pfp_url,
        "bio":      "Advanced Telegram Music Bot — streams songs & videos into voice chats using yt-dlp for high-quality audio.",
        "features": ["YouTube", "Spotify", "Apple Music", "SoundCloud", "Telegram"],
    })

@app.route("/api/botpfp")
def api_botpfp():
    """Serve bot profile picture."""
    pfp_path = "ANNIEMUSIC/assets/bot_pfp.png"
    upic_path = "ANNIEMUSIC/assets/upic.png"
    if os.path.isfile(pfp_path):
        return send_file(pfp_path, mimetype="image/png")
    elif os.path.isfile(upic_path):
        return send_file(upic_path, mimetype="image/png")
    return jsonify({"error": "No profile picture"}), 404

def _fetch_video_via_ytdlp(vid):
    """Fetch video+audio stream URL using android_vr — no cookies needed."""
    url_str = f"https://www.youtube.com/watch?v={vid}"
    try:
        opts = {
            "quiet": True, "no_warnings": True,
            "skip_download": True,
            "format": "bestvideo[height<=720][ext=mp4]+bestaudio/bestvideo[height<=720]+bestaudio/best[height<=720]/best",
            "extractor_args": {
                "youtube": {
                    "player_client": ["android_vr"],
                    "skip": ["hls", "translated_subs"],
                }
            },
            "socket_timeout": 15,
            "retries": 3,
            "nocheckcertificate": True,
            "source_address": "0.0.0.0",
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url_str, download=False)
        if not info:
            return None
        url = info.get("url") or (info.get("requested_formats") or [{}])[0].get("url")
        if not url:
            return None
        dur = int(info.get("duration", 0))
        return {
            "url":      url,
            "ext":      "mp4",
            "title":    info.get("title", "Unknown"),
            "channel":  info.get("channel") or info.get("uploader", ""),
            "duration": _sec_to_min(dur),
            "seconds":  dur,
            "thumb":    f"https://img.youtube.com/vi/{vid}/mqdefault.jpg",
            "ts":       time.time(),
        }
    except Exception:
        return None

_video_cache = {}
_video_lock  = threading.Lock()

def _get_video_data(vid, force_refresh=False):
    if not force_refresh:
        with _video_lock:
            cached = _video_cache.get(vid)
        if cached and _is_url_valid(cached):
            return cached
    data = _fetch_video_via_ytdlp(vid)
    if data:
        with _video_lock:
            _video_cache[vid] = data
    return data

@app.route("/api/video")
def api_video():
    """Proxy video stream from YouTube for web player."""
    vid = request.args.get("v", "").strip()
    if not vid or len(vid) != 11:
        return jsonify({"error": "Invalid video id"}), 400
    try:
        data = _get_video_data(vid)
        if not data or not data.get("url"):
            return jsonify({"error": "Could not fetch video stream"}), 500

        stream_url = data["url"]
        range_header = request.headers.get("Range")
        req_headers = {
            "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept":          "*/*",
            "Accept-Encoding": "identity",
            "Connection":      "keep-alive",
            "Referer":         "https://www.youtube.com/",
        }
        if range_header:
            req_headers["Range"] = range_header

        upstream = requests.get(stream_url, headers=req_headers, stream=True, timeout=30)

        if upstream.status_code in (400, 403, 410):
            upstream.close()
            data = _get_video_data(vid, force_refresh=True)
            if not data or not data.get("url"):
                return jsonify({"error": "Could not refresh video stream"}), 500
            stream_url = data["url"]
            upstream = requests.get(stream_url, headers=req_headers, stream=True, timeout=30)

        resp_headers = {
            "Content-Type":  upstream.headers.get("Content-Type", "video/mp4"),
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache",
        }
        if "Content-Length" in upstream.headers:
            resp_headers["Content-Length"] = upstream.headers["Content-Length"]
        if "Content-Range" in upstream.headers:
            resp_headers["Content-Range"] = upstream.headers["Content-Range"]

        status_code = upstream.status_code

        def generate():
            for chunk in upstream.iter_content(chunk_size=65536):
                if chunk:
                    yield chunk

        return Response(generate(), status=status_code, headers=resp_headers)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/health")
def health():
    return jsonify({"status": "running"}), 200


# ── NSFW Detection API ────────────────────────────────────────────────────────

def _skin_ratio_check(image_bytes: bytes) -> float:
    try:
        from PIL import Image
        import numpy as np
        import io
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = img.resize((300, 300))
        arr = np.array(img, dtype=float)
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        skin_mask = (
            (r > 95) & (g > 40) & (b > 20) &
            (r > g) & (r > b) &
            ((r - g) > 15) &
            (r < 240) & (g < 200) & (b < 180)
        )
        return float(skin_mask.sum()) / (300 * 300)
    except Exception:
        return 0.0


def _nudenet_check(image_bytes: bytes):
    try:
        import io
        from PIL import Image
        from nudenet import NudeDetector
        detector = NudeDetector()
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img.save(tmp_path, "PNG")
        try:
            detections = detector.detect(tmp_path)
            EXPOSED = {
                "FEMALE_GENITALIA_EXPOSED", "MALE_GENITALIA_EXPOSED",
                "FEMALE_BREAST_EXPOSED", "ANUS_EXPOSED", "BUTTOCKS_EXPOSED",
            }
            COVERED = {
                "FEMALE_GENITALIA_COVERED", "FEMALE_BREAST_COVERED",
                "BUTTOCKS_COVERED",
            }
            labels = []
            is_nsfw = False
            for det in detections:
                cls = det.get("class", "")
                score = det.get("score", 0)
                if cls in EXPOSED and score >= 0.50:
                    is_nsfw = True
                    labels.append({"label": cls, "confidence": round(score, 3)})
                elif cls in COVERED and score >= 0.65:
                    is_nsfw = True
                    labels.append({"label": cls, "confidence": round(score, 3)})
            return is_nsfw, labels
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    except Exception:
        return None, []


@app.route("/api/nsfw")
def api_nsfw():
    """
    NSFW Image Detection API
    GET /api/nsfw?url=<image_url>
    Returns: { is_nsfw, method, confidence, labels, by }
    by t.me/PGL_B4CHI
    """
    url = request.args.get("url", "").strip()
    if not url:
        return jsonify({
            "error": "url parameter required",
            "usage": "GET /api/nsfw?url=https://example.com/image.jpg",
            "by": "t.me/PGL_B4CHI"
        }), 400

    try:
        resp = requests.get(url, timeout=12, stream=True)
        if resp.status_code != 200:
            return jsonify({"error": f"Could not fetch image: HTTP {resp.status_code}", "by": "t.me/PGL_B4CHI"}), 400

        content_type = resp.headers.get("Content-Type", "")
        if not any(ct in content_type for ct in ("image/", "application/octet-stream")):
            return jsonify({"error": "URL does not point to an image", "by": "t.me/PGL_B4CHI"}), 400

        image_bytes = b""
        for chunk in resp.iter_content(chunk_size=65536):
            image_bytes += chunk
            if len(image_bytes) > 5_000_000:
                break

        if not image_bytes:
            return jsonify({"error": "Empty image response", "by": "t.me/PGL_B4CHI"}), 400

        # Try NudeNet first (more accurate)
        is_nsfw, labels = _nudenet_check(image_bytes)
        if is_nsfw is not None:
            skin = _skin_ratio_check(image_bytes)
            confidence = max((l["confidence"] for l in labels), default=round(skin, 3))
            return jsonify({
                "is_nsfw": is_nsfw,
                "method": "nudenet",
                "confidence": confidence,
                "skin_ratio": round(skin, 3),
                "labels": labels,
                "by": "t.me/PGL_B4CHI"
            })

        # Fallback: skin ratio
        skin = _skin_ratio_check(image_bytes)
        is_nsfw_skin = skin >= 0.48
        return jsonify({
            "is_nsfw": is_nsfw_skin,
            "method": "skin_ratio",
            "confidence": round(skin, 3),
            "skin_ratio": round(skin, 3),
            "labels": [],
            "by": "t.me/PGL_B4CHI"
        })

    except Exception as e:
        return jsonify({"error": str(e), "by": "t.me/PGL_B4CHI"}), 500


# ── API Documentation Page ────────────────────────────────────────────────────

_API_DOCS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Annie X Music — API Docs</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"/>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#050508;--s1:#0f0f14;--s2:#16161e;--s3:#1e1e28;--s4:#2a2a38;
  --acc:#a855f7;--acc2:#7c3aed;--green:#10b981;--blue:#3b82f6;
  --red:#ef4444;--orange:#f97316;--pink:#ec4899;
  --text:#fff;--text2:#a0a0b8;--text3:#505068;
  --border:rgba(168,85,247,0.15);--border2:rgba(255,255,255,0.07);
}
body{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;min-height:100vh;padding:0}
a{color:var(--acc);text-decoration:none}
a:hover{text-decoration:underline}
code,pre{font-family:'JetBrains Mono',monospace}

/* Header */
.header{background:linear-gradient(135deg,#0f0820 0%,#1a0a2e 50%,#0d1a3a 100%);border-bottom:1px solid var(--border);padding:36px 24px 28px;text-align:center;position:relative;overflow:hidden}
.header::before{content:'';position:absolute;inset:0;background:radial-gradient(ellipse 80% 60% at 50% 0%,rgba(168,85,247,0.12),transparent);pointer-events:none}
.header-badge{display:inline-flex;align-items:center;gap:8px;background:rgba(168,85,247,0.12);border:1px solid rgba(168,85,247,0.3);border-radius:100px;padding:6px 16px;font-size:12px;font-weight:600;color:var(--acc);margin-bottom:16px;letter-spacing:0.5px}
.header-badge::before{content:'●';font-size:8px;color:var(--green);animation:pulse 2s ease infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}
.header h1{font-size:clamp(24px,5vw,40px);font-weight:800;background:linear-gradient(135deg,#fff 0%,#c084fc 60%,#a855f7 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:8px}
.header p{color:var(--text2);font-size:15px;margin-bottom:16px}
.by-link{display:inline-flex;align-items:center;gap:6px;background:rgba(168,85,247,0.1);border:1px solid rgba(168,85,247,0.25);border-radius:8px;padding:8px 16px;font-size:13px;font-weight:600;color:var(--acc);transition:all 0.2s}
.by-link:hover{background:rgba(168,85,247,0.2);text-decoration:none}
.by-link svg{width:16px;height:16px;fill:currentColor}

/* Layout */
.container{max-width:960px;margin:0 auto;padding:32px 20px}

/* Search */
.search-wrap{margin-bottom:32px;position:relative}
.search-wrap input{width:100%;background:var(--s2);border:1px solid var(--border2);border-radius:12px;padding:14px 20px 14px 48px;font-size:14px;color:var(--text);font-family:'Inter',sans-serif;outline:none;transition:border-color 0.2s}
.search-wrap input:focus{border-color:var(--acc)}
.search-wrap input::placeholder{color:var(--text3)}
.search-icon{position:absolute;left:16px;top:50%;transform:translateY(-50%);color:var(--text3)}
.search-icon svg{width:18px;height:18px;fill:currentColor}

/* Stats bar */
.stats-bar{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:32px}
.stat-card{flex:1;min-width:120px;background:var(--s2);border:1px solid var(--border2);border-radius:12px;padding:16px 20px;text-align:center}
.stat-num{font-size:28px;font-weight:800;background:linear-gradient(135deg,var(--acc),var(--pink));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.stat-label{font-size:12px;color:var(--text3);margin-top:2px;text-transform:uppercase;letter-spacing:0.5px;font-weight:600}

/* Section */
.section-title{font-size:13px;font-weight:700;color:var(--text3);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:16px;display:flex;align-items:center;gap:8px}
.section-title::after{content:'';flex:1;height:1px;background:var(--border2)}

/* API Card */
.api-card{background:var(--s2);border:1px solid var(--border2);border-radius:16px;margin-bottom:16px;overflow:hidden;transition:border-color 0.2s;cursor:pointer}
.api-card:hover{border-color:rgba(168,85,247,0.3)}
.api-card.open{border-color:rgba(168,85,247,0.4)}
.api-head{display:flex;align-items:center;gap:12px;padding:16px 20px;user-select:none}
.method{display:inline-block;padding:4px 10px;border-radius:6px;font-size:11px;font-weight:700;font-family:'JetBrains Mono',monospace;letter-spacing:0.5px;flex-shrink:0}
.method.get{background:rgba(16,185,129,0.15);color:var(--green);border:1px solid rgba(16,185,129,0.3)}
.method.post{background:rgba(59,130,246,0.15);color:var(--blue);border:1px solid rgba(59,130,246,0.3)}
.api-path{font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:500;color:var(--text);flex:1}
.api-desc-short{font-size:13px;color:var(--text2);flex:1;text-align:right;margin-left:8px}
.api-toggle{color:var(--text3);transition:transform 0.2s;flex-shrink:0}
.api-toggle svg{width:16px;height:16px;fill:currentColor}
.api-card.open .api-toggle{transform:rotate(180deg)}
.api-body{display:none;border-top:1px solid var(--border2);padding:20px}
.api-card.open .api-body{display:block}

/* Params */
.param-title{font-size:12px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:10px}
.param-row{display:flex;align-items:flex-start;gap:12px;padding:8px 0;border-bottom:1px solid var(--border2)}
.param-row:last-child{border-bottom:none}
.param-name{font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:600;color:var(--acc);min-width:100px}
.param-type{font-size:11px;background:var(--s4);padding:2px 8px;border-radius:4px;color:var(--text2);flex-shrink:0}
.param-req{font-size:10px;background:rgba(239,68,68,0.15);color:var(--red);padding:2px 6px;border-radius:4px;flex-shrink:0;font-weight:600}
.param-opt{font-size:10px;background:rgba(80,80,104,0.3);color:var(--text3);padding:2px 6px;border-radius:4px;flex-shrink:0}
.param-desc{font-size:13px;color:var(--text2);flex:1}

/* Code block */
.code-wrap{margin-top:14px}
.code-label{font-size:11px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;display:flex;align-items:center;justify-content:space-between}
.copy-btn{background:var(--s4);border:none;color:var(--text2);padding:4px 10px;border-radius:6px;font-size:11px;cursor:pointer;font-family:'Inter',sans-serif;transition:all 0.15s}
.copy-btn:hover{background:var(--acc);color:#fff}
pre{background:var(--s3);border:1px solid var(--border2);border-radius:10px;padding:14px 16px;font-size:12px;line-height:1.6;overflow-x:auto;color:#e2e8f0}
pre .key{color:#c084fc}
pre .str{color:#86efac}
pre .num{color:#fbbf24}
pre .bool{color:#60a5fa}

/* Response badge */
.response-tags{display:flex;gap:6px;flex-wrap:wrap;margin-top:14px}
.resp-tag{padding:4px 10px;border-radius:6px;font-size:11px;font-weight:600}
.resp-200{background:rgba(16,185,129,0.12);color:var(--green);border:1px solid rgba(16,185,129,0.25)}
.resp-400{background:rgba(239,68,68,0.1);color:var(--red);border:1px solid rgba(239,68,68,0.2)}
.resp-500{background:rgba(249,115,22,0.1);color:var(--orange);border:1px solid rgba(249,115,22,0.2)}

/* Footer */
.footer{text-align:center;padding:40px 20px;color:var(--text3);font-size:13px}
.footer a{color:var(--acc)}

/* Base URL box */
.base-url-box{background:linear-gradient(135deg,rgba(168,85,247,0.08),rgba(59,130,246,0.06));border:1px solid rgba(168,85,247,0.25);border-radius:14px;padding:16px 20px;margin-bottom:24px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.base-url-label{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--acc);flex-shrink:0}
.base-url-value{font-family:'JetBrains Mono',monospace;font-size:13px;color:#c084fc;flex:1;word-break:break-all}
.base-url-copy{background:rgba(168,85,247,0.15);border:1px solid rgba(168,85,247,0.3);border-radius:8px;color:var(--acc);padding:6px 14px;font-size:12px;font-weight:600;cursor:pointer;font-family:'Inter',sans-serif;transition:all 0.15s;flex-shrink:0}
.base-url-copy:hover{background:var(--acc);color:#fff}

/* Usage card */
.usage-card{background:var(--s2);border:1px solid var(--border2);border-radius:16px;margin-bottom:24px;overflow:hidden}
.usage-head{display:flex;align-items:center;gap:12px;padding:16px 20px;cursor:pointer;user-select:none}
.usage-head:hover .usage-title{color:var(--acc)}
.usage-icon{width:32px;height:32px;background:rgba(168,85,247,0.12);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0}
.usage-title{font-size:15px;font-weight:700;color:var(--text);flex:1}
.usage-sub{font-size:12px;color:var(--text3);margin-top:2px}
.usage-toggle{color:var(--text3);transition:transform 0.2s;flex-shrink:0}
.usage-toggle svg{width:16px;height:16px;fill:currentColor}
.usage-card.open .usage-toggle{transform:rotate(180deg)}
.usage-body{display:none;border-top:1px solid var(--border2);padding:20px}
.usage-card.open .usage-body{display:block}
.lang-tabs{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}
.lang-tab{background:var(--s4);border:1px solid var(--border2);border-radius:8px;padding:6px 14px;font-size:12px;font-weight:600;cursor:pointer;color:var(--text2);font-family:'Inter',sans-serif;transition:all 0.15s}
.lang-tab.active,.lang-tab:hover{background:rgba(168,85,247,0.15);border-color:rgba(168,85,247,0.3);color:var(--acc)}
.code-tab{display:none}
.code-tab.active{display:block}
.usage-note{background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.2);border-radius:10px;padding:12px 16px;font-size:13px;color:#6ee7b7;margin-bottom:16px}
.usage-note strong{color:var(--green)}

/* Mobile */
@media(max-width:600px){
  .api-desc-short{display:none}
  .stats-bar{gap:8px}
  .base-url-box{gap:8px}
}
</style>
</head>
<body>
<div class="header">
  <div class="header-badge">
    <span>API</span>
    <span>Live &amp; Free</span>
  </div>
  <h1>Annie X Music API</h1>
  <p>Public REST API for music, search, NSFW detection &amp; more</p>
  <a class="by-link" href="https://t.me/PGL_B4CHI" target="_blank">
    <svg viewBox="0 0 24 24"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221l-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12L7.8 13.917l-2.963-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.351 1.642z"/></svg>
    by t.me/PGL_B4CHI
  </a>
</div>

<div class="container">
  <div class="search-wrap">
    <span class="search-icon"><svg viewBox="0 0 24 24"><path d="M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/></svg></span>
    <input type="text" id="search" placeholder="Search APIs..." oninput="filterApis(this.value)"/>
  </div>

  <div class="stats-bar">
    <div class="stat-card"><div class="stat-num">9</div><div class="stat-label">Endpoints</div></div>
    <div class="stat-card"><div class="stat-num">Free</div><div class="stat-label">No Auth</div></div>
    <div class="stat-card"><div class="stat-num">REST</div><div class="stat-label">JSON API</div></div>
    <div class="stat-card"><div class="stat-num">24/7</div><div class="stat-label">Uptime</div></div>
  </div>

  <div class="base-url-box">
    <span class="base-url-label">🌐 Base URL</span>
    <span class="base-url-value" id="baseUrl"></span>
    <button class="base-url-copy" onclick="copyBaseUrl()">Copy</button>
  </div>

  <div class="usage-card open" id="usageCard">
    <div class="usage-head" onclick="toggleUsage()">
      <div class="usage-icon">🤖</div>
      <div style="flex:1">
        <div class="usage-title">Apne Bot mein kaise use karein</div>
        <div class="usage-sub">Python · Pyrogram · aiohttp · Node.js · cURL — sab endpoints ke liye ready code</div>
      </div>
      <span class="usage-toggle"><svg viewBox="0 0 24 24"><path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/></svg></span>
    </div>
    <div class="usage-body">
      <div class="usage-note">
        <strong>✅ Bilkul Free!</strong> Koi API key nahi chahiye. Sirf BASE_URL apne bot mein copy karo aur neeche diye gaye ready-made code use karo.
      </div>
      <div class="lang-tabs">
        <button class="lang-tab active" onclick="switchTab('python')">Python</button>
        <button class="lang-tab" onclick="switchTab('pyrogram')">Pyrogram Bot</button>
        <button class="lang-tab" onclick="switchTab('aiohttp')">aiohttp (async)</button>
        <button class="lang-tab" onclick="switchTab('nodejs')">Node.js</button>
        <button class="lang-tab" onclick="switchTab('curl')">cURL</button>
      </div>

      <!-- ─── Python ─── -->
      <div class="code-tab active" id="tab-python">
        <div class="code-label">Setup <button class="copy-btn" onclick="copyCode('py-setup')">Copy</button></div>
        <pre id="py-setup">import requests

BASE_URL = "<span id="py-base-url">https://yourbot.replit.dev</span>"</pre>

        <div class="code-label" style="margin-top:14px">🎵 /api/play — Song name ya URL se play karo <button class="copy-btn" onclick="copyCode('py-play')">Copy</button></div>
        <pre id="py-play">res = requests.get(f"{BASE_URL}/api/play", params={"q": "Tum Hi Ho Arijit Singh"})
data = res.json()
print(data["title"])        # Tum Hi Ho
print(data["duration"])     # 4:22
print(data["stream_url"])   # Direct YouTube audio URL
print(data["audio_proxy"])  # Proxy URL (CORS-free, use this in browser)
print(data["download"])     # Download link</pre>

        <div class="code-label" style="margin-top:14px">🔍 /api/search — YouTube par search karo <button class="copy-btn" onclick="copyCode('py-search')">Copy</button></div>
        <pre id="py-search">res = requests.get(f"{BASE_URL}/api/search", params={"q": "Arijit Singh"})
for song in res.json()["results"]:
    print(song["id"], song["title"], song["duration"])</pre>

        <div class="code-label" style="margin-top:14px">📊 /api/stream — Video ki metadata lo <button class="copy-btn" onclick="copyCode('py-stream')">Copy</button></div>
        <pre id="py-stream">res = requests.get(f"{BASE_URL}/api/stream", params={"v": "dQw4w9WgXcQ"})
info = res.json()
print(info["title"], info["channel"], info["duration"])</pre>

        <div class="code-label" style="margin-top:14px">🔥 /api/trending — Trending songs lo <button class="copy-btn" onclick="copyCode('py-trend')">Copy</button></div>
        <pre id="py-trend">res = requests.get(f"{BASE_URL}/api/trending")
for s in res.json()["songs"][:5]:
    print(f"[{s['category']}] {s['title']} — {s['duration']}")</pre>

        <div class="code-label" style="margin-top:14px">🔗 /api/related — Related songs lo <button class="copy-btn" onclick="copyCode('py-related')">Copy</button></div>
        <pre id="py-related">res = requests.get(f"{BASE_URL}/api/related", params={"v": "dQw4w9WgXcQ"})
for s in res.json()["results"]:
    print(s["title"], s["duration"])</pre>

        <div class="code-label" style="margin-top:14px">⬇️ /api/download — Audio file download karo <button class="copy-btn" onclick="copyCode('py-dl')">Copy</button></div>
        <pre id="py-dl">res = requests.get(f"{BASE_URL}/api/download", params={"v": "dQw4w9WgXcQ"}, stream=True)
with open("song.m4a", "wb") as f:
    for chunk in res.iter_content(65536):
        f.write(chunk)
print("Download complete!")</pre>

        <div class="code-label" style="margin-top:14px">🔞 /api/nsfw — Image check karo <button class="copy-btn" onclick="copyCode('py-nsfw')">Copy</button></div>
        <pre id="py-nsfw">res = requests.get(f"{BASE_URL}/api/nsfw", params={"url": "https://example.com/image.jpg"})
data = res.json()
if data["is_nsfw"]:
    print(f"NSFW detected! Confidence: {data['confidence']}")
else:
    print("Image is safe")</pre>
      </div>

      <!-- ─── Pyrogram Bot ─── -->
      <div class="code-tab" id="tab-pyrogram">
        <div class="code-label">Complete Pyrogram Bot — Sab endpoints ke saath <button class="copy-btn" onclick="copyCode('pyro-full')">Copy</button></div>
        <pre id="pyro-full">import requests
from pyrogram import Client, filters

BASE_URL = "<span id="pyro-base-url">https://yourbot.replit.dev</span>"
app = Client("mybot", api_id=123456, api_hash="your_hash", bot_token="your_token")

# /play — Song name se play info lo
@app.on_message(filters.command("play"))
async def play_song(client, message):
    query = " ".join(message.command[1:])
    if not query:
        return await message.reply("Usage: /play &lt;song name ya YouTube URL&gt;")
    msg = await message.reply("🔍 Searching...")
    res = requests.get(f"{BASE_URL}/api/play", params={"q": query})
    if res.status_code != 200:
        return await msg.edit("❌ Song nahi mila!")
    d = res.json()
    text = (
        f"🎵 **{d['title']}**\n"
        f"👤 {d['channel']}\n"
        f"⏱ {d['duration']}\n"
        f"🔗 [YouTube]({d['youtube_url']}) | [Download]({d['download']})\n\n"
        f"▶️ Stream: `{d['audio_proxy']}`"
    )
    await msg.edit(text, disable_web_page_preview=True)

# /search — YouTube search
@app.on_message(filters.command("search"))
async def search_song(client, message):
    query = " ".join(message.command[1:])
    if not query:
        return await message.reply("Usage: /search &lt;song name&gt;")
    res = requests.get(f"{BASE_URL}/api/search", params={"q": query})
    results = res.json().get("results", [])
    if not results:
        return await message.reply("❌ Koi result nahi mila!")
    text = "🎵 **Search Results:**\n\n"
    for i, s in enumerate(results[:5], 1):
        text += f"{i}. [{s['title']}](https://youtu.be/{s['id']}) — {s['duration']}\n"
    await message.reply(text)

# /trending — Trending songs
@app.on_message(filters.command("trending"))
async def trending_songs(client, message):
    res = requests.get(f"{BASE_URL}/api/trending")
    songs = res.json().get("songs", [])[:8]
    text = "🔥 **Trending Songs:**\n\n"
    for i, s in enumerate(songs, 1):
        text += f"{i}. [{s['title']}](https://youtu.be/{s['id']}) [{s['category']}]\n"
    await message.reply(text)

# NSFW guard — group mein photo check karo
@app.on_message(filters.photo &amp; filters.group)
async def nsfw_check(client, message):
    photo = message.photo
    file_url = await client.get_file_url(photo.file_id) if hasattr(photo, "file_id") else None
    if not file_url:
        return
    res = requests.get(f"{BASE_URL}/api/nsfw", params={"url": file_url})
    if res.json().get("is_nsfw"):
        await message.delete()
        await message.chat.send_message("⛔ NSFW content remove kar diya gaya!")

app.run()</pre>
      </div>

      <!-- ─── aiohttp async ─── -->
      <div class="code-tab" id="tab-aiohttp">
        <div class="code-label">Complete async wrapper — sab endpoints <button class="copy-btn" onclick="copyCode('aio-full')">Copy</button></div>
        <pre id="aio-full">import aiohttp
import asyncio

BASE_URL = "<span id="aio-base-url">https://yourbot.replit.dev</span>"

class AnnieAPI:
    def __init__(self, base_url: str):
        self.base = base_url

    async def play(self, query: str) -> dict:
        # Song name / URL / video ID se full play info lo
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{self.base}/api/play", params={"q": query}) as r:
                return await r.json()

    async def search(self, query: str) -> list:
        # YouTube par search karo
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{self.base}/api/search", params={"q": query}) as r:
                data = await r.json()
                return data.get("results", [])

    async def stream(self, video_id: str) -> dict:
        # Video ki metadata lo
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{self.base}/api/stream", params={"v": video_id}) as r:
                return await r.json()

    async def trending(self) -> list:
        # Trending songs lo
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{self.base}/api/trending") as r:
                data = await r.json()
                return data.get("songs", [])

    async def related(self, video_id: str) -> list:
        # Related songs lo
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{self.base}/api/related", params={"v": video_id}) as r:
                data = await r.json()
                return data.get("results", [])

    async def check_nsfw(self, image_url: str) -> bool:
        # Image NSFW hai ya nahi check karo
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{self.base}/api/nsfw", params={"url": image_url}) as r:
                data = await r.json()
                return data.get("is_nsfw", False)

# ── Usage ────────────────────────────────────────────────────────
api = AnnieAPI(BASE_URL)

async def main():
    # Play
    info = await api.play("Tum Hi Ho Arijit Singh")
    print(f"Playing: {info['title']} ({info['duration']})")
    print(f"Stream: {info['audio_proxy']}")

    # Search
    results = await api.search("Punjabi songs")
    for r in results[:3]:
        print(r["title"], r["duration"])

    # Trending
    songs = await api.trending()
    print(f"Trending: {len(songs)} songs")

    # NSFW check
    safe = await api.check_nsfw("https://example.com/image.jpg")
    print(f"Is NSFW: {safe}")

asyncio.run(main())</pre>
      </div>

      <!-- ─── Node.js ─── -->
      <div class="code-tab" id="tab-nodejs">
        <div class="code-label">Node.js — Complete wrapper (fetch built-in) <button class="copy-btn" onclick="copyCode('node-full')">Copy</button></div>
        <pre id="node-full">const BASE_URL = "<span id="node-base-url">https://yourbot.replit.dev</span>";

const api = {
  // 🎵 Song name ya URL se play info lo
  async play(query) {
    const res = await fetch(`${BASE_URL}/api/play?q=${encodeURIComponent(query)}`);
    return res.json();
  },

  // 🔍 YouTube search
  async search(query) {
    const res = await fetch(`${BASE_URL}/api/search?q=${encodeURIComponent(query)}`);
    const data = await res.json();
    return data.results || [];
  },

  // 📊 Video metadata
  async stream(videoId) {
    const res = await fetch(`${BASE_URL}/api/stream?v=${videoId}`);
    return res.json();
  },

  // 🔥 Trending songs
  async trending() {
    const res = await fetch(`${BASE_URL}/api/trending`);
    const data = await res.json();
    return data.songs || [];
  },

  // 🔗 Related songs
  async related(videoId) {
    const res = await fetch(`${BASE_URL}/api/related?v=${videoId}`);
    const data = await res.json();
    return data.results || [];
  },

  // ⬇️ Download link lo
  download(videoId) {
    return `${BASE_URL}/api/download?v=${videoId}`;
  },

  // 🎧 Audio proxy URL lo (browser player ke liye)
  audioProxy(videoId) {
    return `${BASE_URL}/api/audio?v=${videoId}`;
  },

  // 🔞 NSFW check
  async checkNsfw(imageUrl) {
    const res = await fetch(`${BASE_URL}/api/nsfw?url=${encodeURIComponent(imageUrl)}`);
    const data = await res.json();
    return data;
  },
};

// ── Example usage ────────────────────────────────────────────────
(async () => {
  // Play a song
  const info = await api.play("Tum Hi Ho Arijit Singh");
  console.log(`Title: ${info.title}`);
  console.log(`Duration: ${info.duration}`);
  console.log(`Stream URL: ${info.audio_proxy}`);
  console.log(`Download: ${info.download}`);

  // Search
  const results = await api.search("Punjabi hits");
  results.slice(0, 3).forEach(s => console.log(s.title, s.duration));

  // Trending
  const trending = await api.trending();
  console.log(`${trending.length} trending songs`);
})();</pre>
      </div>

      <!-- ─── cURL ─── -->
      <div class="code-tab" id="tab-curl">
        <div class="code-label">cURL — Sab endpoints <button class="copy-btn" onclick="copyCode('curl-all')">Copy</button></div>
        <pre id="curl-all">BASE="<span id="curl-base-url">https://yourbot.replit.dev</span>"

# 🎵 Play — song name se
curl "$BASE/api/play?q=Tum+Hi+Ho+Arijit+Singh"

# 🎵 Play — video ID se
curl "$BASE/api/play?v=dQw4w9WgXcQ"

# 🔍 Search
curl "$BASE/api/search?q=Arijit+Singh"

# 📊 Stream metadata
curl "$BASE/api/stream?v=dQw4w9WgXcQ"

# 🔥 Trending songs
curl "$BASE/api/trending"

# 🔗 Related songs
curl "$BASE/api/related?v=dQw4w9WgXcQ"

# 🎧 Audio proxy stream (browser player ke liye)
curl "$BASE/api/audio?v=dQw4w9WgXcQ"

# ⬇️ Download as file
curl -O -J "$BASE/api/download?v=dQw4w9WgXcQ"

# 🔞 NSFW check
curl "$BASE/api/nsfw?url=https://example.com/image.jpg"</pre>
      </div>

    </div>
  </div>

  <div class="section-title">Music &amp; YouTube</div>

  <div class="api-card" data-tags="search youtube music">
    <div class="api-head" onclick="toggle(this)">
      <span class="method get">GET</span>
      <span class="api-path">/api/search</span>
      <span class="api-desc-short">Search songs on YouTube</span>
      <span class="api-toggle"><svg viewBox="0 0 24 24"><path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/></svg></span>
    </div>
    <div class="api-body">
      <p style="color:var(--text2);font-size:14px;margin-bottom:14px">Search YouTube for songs. Returns a list of results with title, channel, duration and thumbnail.</p>
      <div class="param-title">Parameters</div>
      <div class="param-row">
        <span class="param-name">q</span>
        <span class="param-type">string</span>
        <span class="param-req">required</span>
        <span class="param-desc">Search query (e.g. "Arijit Singh new song")</span>
      </div>
      <div class="code-wrap">
        <div class="code-label">Example Request <button class="copy-btn" onclick="copyCode('ex1')">Copy</button></div>
        <pre id="ex1">GET /api/search?q=Arijit+Singh</pre>
      </div>
      <div class="code-wrap">
        <div class="code-label">Response</div>
        <pre><span class="key">"results"</span>: [
  {
    <span class="key">"id"</span>: <span class="str">"dQw4w9WgXcQ"</span>,
    <span class="key">"title"</span>: <span class="str">"Song Title"</span>,
    <span class="key">"channel"</span>: <span class="str">"Channel Name"</span>,
    <span class="key">"duration"</span>: <span class="str">"4:32"</span>,
    <span class="key">"thumb"</span>: <span class="str">"https://img.youtube.com/..."</span>
  }
]</pre>
      </div>
      <div class="response-tags">
        <span class="resp-tag resp-200">200 OK</span>
        <span class="resp-tag resp-400">400 Missing q</span>
        <span class="resp-tag resp-500">500 Error</span>
      </div>
    </div>
  </div>

  <div class="api-card" data-tags="stream metadata youtube video">
    <div class="api-head" onclick="toggle(this)">
      <span class="method get">GET</span>
      <span class="api-path">/api/stream</span>
      <span class="api-desc-short">Get video metadata</span>
      <span class="api-toggle"><svg viewBox="0 0 24 24"><path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/></svg></span>
    </div>
    <div class="api-body">
      <p style="color:var(--text2);font-size:14px;margin-bottom:14px">Get metadata for a YouTube video — title, channel, duration, thumbnail.</p>
      <div class="param-title">Parameters</div>
      <div class="param-row">
        <span class="param-name">v</span>
        <span class="param-type">string</span>
        <span class="param-req">required</span>
        <span class="param-desc">YouTube video ID (11 chars, e.g. dQw4w9WgXcQ)</span>
      </div>
      <div class="code-wrap">
        <div class="code-label">Example <button class="copy-btn" onclick="copyCode('ex2')">Copy</button></div>
        <pre id="ex2">GET /api/stream?v=dQw4w9WgXcQ</pre>
      </div>
      <div class="code-wrap">
        <div class="code-label">Response</div>
        <pre>{
  <span class="key">"title"</span>: <span class="str">"Never Gonna Give You Up"</span>,
  <span class="key">"channel"</span>: <span class="str">"Rick Astley"</span>,
  <span class="key">"duration"</span>: <span class="str">"3:33"</span>,
  <span class="key">"seconds"</span>: <span class="num">213</span>,
  <span class="key">"thumb"</span>: <span class="str">"https://img.youtube.com/vi/.../mqdefault.jpg"</span>
}</pre>
      </div>
      <div class="response-tags"><span class="resp-tag resp-200">200 OK</span><span class="resp-tag resp-400">400 Invalid ID</span></div>
    </div>
  </div>

  <div class="api-card" data-tags="play song music youtube search stream bot">
    <div class="api-head" onclick="toggle(this)">
      <span class="method get">GET</span>
      <span class="api-path">/api/play</span>
      <span class="api-desc-short">Bot-style play — search &amp; stream</span>
      <span class="api-toggle"><svg viewBox="0 0 24 24"><path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/></svg></span>
    </div>
    <div class="api-body">
      <p style="color:var(--text2);font-size:14px;margin-bottom:14px">Exactly what the bot does when you send /play — accepts a song name, YouTube URL, or video ID. Returns full metadata + direct stream URL + audio proxy URL ready to use.</p>
      <div class="param-title">Parameters</div>
      <div class="param-row">
        <span class="param-name">q</span>
        <span class="param-type">string</span>
        <span class="param-opt">optional*</span>
        <span class="param-desc">Song name, search query, or YouTube URL (e.g. "Tum Hi Ho" or https://youtu.be/...)</span>
      </div>
      <div class="param-row">
        <span class="param-name">v</span>
        <span class="param-type">string</span>
        <span class="param-opt">optional*</span>
        <span class="param-desc">YouTube video ID (11 chars). Use this if you already have the ID.</span>
      </div>
      <p style="color:var(--text3);font-size:12px;margin-top:8px">* At least one of <code>q</code> or <code>v</code> is required.</p>
      <div class="code-wrap">
        <div class="code-label">Example — by song name <button class="copy-btn" onclick="copyCode('play1')">Copy</button></div>
        <pre id="play1">GET /api/play?q=Tum+Hi+Ho+Arijit+Singh</pre>
      </div>
      <div class="code-wrap">
        <div class="code-label">Example — by YouTube URL <button class="copy-btn" onclick="copyCode('play2')">Copy</button></div>
        <pre id="play2">GET /api/play?q=https://youtu.be/dQw4w9WgXcQ</pre>
      </div>
      <div class="code-wrap">
        <div class="code-label">Example — by video ID <button class="copy-btn" onclick="copyCode('play3')">Copy</button></div>
        <pre id="play3">GET /api/play?v=dQw4w9WgXcQ</pre>
      </div>
      <div class="code-wrap">
        <div class="code-label">Response</div>
        <pre>{
  <span class="key">"id"</span>:          <span class="str">"dQw4w9WgXcQ"</span>,
  <span class="key">"title"</span>:       <span class="str">"Tum Hi Ho"</span>,
  <span class="key">"channel"</span>:     <span class="str">"T-Series"</span>,
  <span class="key">"duration"</span>:    <span class="str">"4:22"</span>,
  <span class="key">"seconds"</span>:     <span class="num">262</span>,
  <span class="key">"thumb"</span>:       <span class="str">"https://img.youtube.com/vi/dQw4w9WgXcQ/mqdefault.jpg"</span>,
  <span class="key">"youtube_url"</span>: <span class="str">"https://www.youtube.com/watch?v=dQw4w9WgXcQ"</span>,
  <span class="key">"stream_url"</span>:  <span class="str">"https://rr3---sn-....googlevideo.com/..."</span>,
  <span class="key">"audio_proxy"</span>: <span class="str">"https://yourbot.replit.dev/api/audio?v=dQw4w9WgXcQ"</span>,
  <span class="key">"download"</span>:    <span class="str">"https://yourbot.replit.dev/api/download?v=dQw4w9WgXcQ"</span>
}</pre>
      </div>
      <div class="response-tags">
        <span class="resp-tag resp-200">200 OK</span>
        <span class="resp-tag resp-400">400 Missing params</span>
        <span class="resp-tag resp-400" style="background:rgba(239,68,68,0.1);color:var(--red);border:1px solid rgba(239,68,68,0.2)">404 Not found</span>
        <span class="resp-tag resp-500">500 Error</span>
      </div>
    </div>
  </div>

  <div class="api-card" data-tags="audio proxy youtube download stream">
    <div class="api-head" onclick="toggle(this)">
      <span class="method get">GET</span>
      <span class="api-path">/api/audio</span>
      <span class="api-desc-short">Proxy audio stream</span>
      <span class="api-toggle"><svg viewBox="0 0 24 24"><path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/></svg></span>
    </div>
    <div class="api-body">
      <p style="color:var(--text2);font-size:14px;margin-bottom:14px">Proxy audio stream from YouTube — bypasses CORS. Returns audio/mp4 or audio/webm stream. Supports Range requests.</p>
      <div class="param-title">Parameters</div>
      <div class="param-row">
        <span class="param-name">v</span>
        <span class="param-type">string</span>
        <span class="param-req">required</span>
        <span class="param-desc">YouTube video ID</span>
      </div>
      <div class="code-wrap">
        <div class="code-label">Example <button class="copy-btn" onclick="copyCode('ex3')">Copy</button></div>
        <pre id="ex3">GET /api/audio?v=dQw4w9WgXcQ</pre>
      </div>
      <div class="response-tags"><span class="resp-tag resp-200">200 Audio Stream</span><span class="resp-tag resp-400">400 Invalid ID</span><span class="resp-tag resp-500">503 Unavailable</span></div>
    </div>
  </div>

  <div class="api-card" data-tags="download youtube audio file">
    <div class="api-head" onclick="toggle(this)">
      <span class="method get">GET</span>
      <span class="api-path">/api/download</span>
      <span class="api-desc-short">Download audio file</span>
      <span class="api-toggle"><svg viewBox="0 0 24 24"><path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/></svg></span>
    </div>
    <div class="api-body">
      <p style="color:var(--text2);font-size:14px;margin-bottom:14px">Download audio as a file with Content-Disposition header. Opens download dialog in browser.</p>
      <div class="param-title">Parameters</div>
      <div class="param-row">
        <span class="param-name">v</span>
        <span class="param-type">string</span>
        <span class="param-req">required</span>
        <span class="param-desc">YouTube video ID</span>
      </div>
      <div class="code-wrap">
        <div class="code-label">Example <button class="copy-btn" onclick="copyCode('ex4')">Copy</button></div>
        <pre id="ex4">GET /api/download?v=dQw4w9WgXcQ</pre>
      </div>
      <div class="response-tags"><span class="resp-tag resp-200">200 File Download</span><span class="resp-tag resp-500">500 Error</span></div>
    </div>
  </div>

  <div class="api-card" data-tags="video proxy youtube">
    <div class="api-head" onclick="toggle(this)">
      <span class="method get">GET</span>
      <span class="api-path">/api/video</span>
      <span class="api-desc-short">Proxy video stream</span>
      <span class="api-toggle"><svg viewBox="0 0 24 24"><path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/></svg></span>
    </div>
    <div class="api-body">
      <p style="color:var(--text2);font-size:14px;margin-bottom:14px">Proxy video+audio stream from YouTube for web player. Returns video/mp4 stream.</p>
      <div class="param-title">Parameters</div>
      <div class="param-row">
        <span class="param-name">v</span>
        <span class="param-type">string</span>
        <span class="param-req">required</span>
        <span class="param-desc">YouTube video ID</span>
      </div>
      <div class="code-wrap">
        <div class="code-label">Example <button class="copy-btn" onclick="copyCode('ex5')">Copy</button></div>
        <pre id="ex5">GET /api/video?v=dQw4w9WgXcQ</pre>
      </div>
      <div class="response-tags"><span class="resp-tag resp-200">200 Video Stream</span><span class="resp-tag resp-500">500 Error</span></div>
    </div>
  </div>

  <div class="api-card" data-tags="trending songs youtube music">
    <div class="api-head" onclick="toggle(this)">
      <span class="method get">GET</span>
      <span class="api-path">/api/trending</span>
      <span class="api-desc-short">Trending songs</span>
      <span class="api-toggle"><svg viewBox="0 0 24 24"><path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/></svg></span>
    </div>
    <div class="api-body">
      <p style="color:var(--text2);font-size:14px;margin-bottom:14px">Get trending songs — Hindi, Punjabi, Bollywood, International. Updated every 30 minutes. No parameters needed.</p>
      <div class="code-wrap">
        <div class="code-label">Example <button class="copy-btn" onclick="copyCode('ex6')">Copy</button></div>
        <pre id="ex6">GET /api/trending</pre>
      </div>
      <div class="code-wrap">
        <div class="code-label">Response</div>
        <pre>{
  <span class="key">"songs"</span>: [
    {
      <span class="key">"id"</span>: <span class="str">"abc123"</span>,
      <span class="key">"title"</span>: <span class="str">"Song Name"</span>,
      <span class="key">"channel"</span>: <span class="str">"Artist"</span>,
      <span class="key">"duration"</span>: <span class="str">"3:45"</span>,
      <span class="key">"category"</span>: <span class="str">"Hindi"</span>,
      <span class="key">"thumb"</span>: <span class="str">"https://..."</span>
    }
  ]
}</pre>
      </div>
      <div class="response-tags"><span class="resp-tag resp-200">200 OK</span></div>
    </div>
  </div>

  <div class="api-card" data-tags="related songs youtube recommendations">
    <div class="api-head" onclick="toggle(this)">
      <span class="method get">GET</span>
      <span class="api-path">/api/related</span>
      <span class="api-desc-short">Related songs</span>
      <span class="api-toggle"><svg viewBox="0 0 24 24"><path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/></svg></span>
    </div>
    <div class="api-body">
      <p style="color:var(--text2);font-size:14px;margin-bottom:14px">Get related/recommended songs for a given video ID.</p>
      <div class="param-title">Parameters</div>
      <div class="param-row">
        <span class="param-name">v</span>
        <span class="param-type">string</span>
        <span class="param-req">required</span>
        <span class="param-desc">YouTube video ID</span>
      </div>
      <div class="code-wrap">
        <div class="code-label">Example <button class="copy-btn" onclick="copyCode('ex7')">Copy</button></div>
        <pre id="ex7">GET /api/related?v=dQw4w9WgXcQ</pre>
      </div>
      <div class="response-tags"><span class="resp-tag resp-200">200 OK</span><span class="resp-tag resp-400">400 Invalid ID</span></div>
    </div>
  </div>

  <div class="section-title" style="margin-top:32px">NSFW Detection</div>

  <div class="api-card" data-tags="nsfw detection image adult content check">
    <div class="api-head" onclick="toggle(this)">
      <span class="method get">GET</span>
      <span class="api-path">/api/nsfw</span>
      <span class="api-desc-short">Detect adult content in images</span>
      <span class="api-toggle"><svg viewBox="0 0 24 24"><path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/></svg></span>
    </div>
    <div class="api-body">
      <p style="color:var(--text2);font-size:14px;margin-bottom:14px">Check if an image URL contains NSFW / adult / explicit content. Uses AI-based detection (NudeNet) with skin-ratio fallback. Max image size: 5MB.</p>
      <div class="param-title">Parameters</div>
      <div class="param-row">
        <span class="param-name">url</span>
        <span class="param-type">string</span>
        <span class="param-req">required</span>
        <span class="param-desc">Direct URL to the image (jpg, png, webp, gif)</span>
      </div>
      <div class="code-wrap">
        <div class="code-label">Example <button class="copy-btn" onclick="copyCode('ex11')">Copy</button></div>
        <pre id="ex11">GET /api/nsfw?url=https://example.com/image.jpg</pre>
      </div>
      <div class="code-wrap">
        <div class="code-label">Response (Safe image)</div>
        <pre>{
  <span class="key">"is_nsfw"</span>: <span class="bool">false</span>,
  <span class="key">"method"</span>: <span class="str">"nudenet"</span>,
  <span class="key">"confidence"</span>: <span class="num">0.12</span>,
  <span class="key">"skin_ratio"</span>: <span class="num">0.08</span>,
  <span class="key">"labels"</span>: [],
  <span class="key">"by"</span>: <span class="str">"t.me/PGL_B4CHI"</span>
}</pre>
      </div>
      <div class="code-wrap">
        <div class="code-label">Response (NSFW image)</div>
        <pre>{
  <span class="key">"is_nsfw"</span>: <span class="bool">true</span>,
  <span class="key">"method"</span>: <span class="str">"nudenet"</span>,
  <span class="key">"confidence"</span>: <span class="num">0.87</span>,
  <span class="key">"skin_ratio"</span>: <span class="num">0.54</span>,
  <span class="key">"labels"</span>: [{ <span class="key">"label"</span>: <span class="str">"FEMALE_BREAST_EXPOSED"</span>, <span class="key">"confidence"</span>: <span class="num">0.87</span> }],
  <span class="key">"by"</span>: <span class="str">"t.me/PGL_B4CHI"</span>
}</pre>
      </div>
      <div class="response-tags">
        <span class="resp-tag resp-200">200 OK</span>
        <span class="resp-tag resp-400">400 Missing url / Not an image</span>
        <span class="resp-tag resp-500">500 Error</span>
      </div>
    </div>
  </div>


</div>

<div class="footer">
  <p>Built with ❤️ &nbsp;|&nbsp; <a href="https://t.me/PGL_B4CHI" target="_blank">@PGL_B4CHI</a> &nbsp;|&nbsp; <a href="/">🎵 Music Player</a></p>
  <p style="margin-top:8px;font-size:12px">Annie X Music API — Free, No auth required, 24/7</p>
</div>

<script>
// ── Base URL auto-detect ─────────────────────────────────────────
(function(){
  const base = window.location.origin;
  ['py-base-url','pyro-base-url','aio-base-url','node-base-url','curl-base-url','baseUrl'].forEach(id=>{
    const el = document.getElementById(id);
    if(el) el.textContent = base;
  });
})();

function copyBaseUrl(){
  const val = document.getElementById('baseUrl')?.textContent || window.location.origin;
  navigator.clipboard.writeText(val).then(()=>{
    const btn = document.querySelector('[onclick="copyBaseUrl()"]');
    if(btn){btn.textContent='Copied!';setTimeout(()=>btn.textContent='Copy',1500)}
  });
}

// ── Toggle API card ──────────────────────────────────────────────
function toggle(head){
  const card = head.closest('.api-card');
  card.classList.toggle('open');
}

// ── Copy code ────────────────────────────────────────────────────
function copyCode(id){
  const el = document.getElementById(id);
  if(!el) return;
  navigator.clipboard.writeText(el.innerText).then(()=>{
    const btn = document.querySelector(`[onclick="copyCode('${id}')"]`);
    if(btn){btn.textContent='Copied!';setTimeout(()=>btn.textContent='Copy',1500)}
  });
}

// ── Language tabs ────────────────────────────────────────────────
function switchTab(lang){
  document.querySelectorAll('.lang-tab').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.code-tab').forEach(t => t.classList.remove('active'));
  const activeBtn = document.querySelector(`.lang-tab[onclick="switchTab('${lang}')"]`);
  const activeTab = document.getElementById('tab-' + lang);
  if(activeBtn) activeBtn.classList.add('active');
  if(activeTab) activeTab.classList.add('active');
}

// ── Usage card toggle ─────────────────────────────────────────────
function toggleUsage(){
  const card = document.getElementById('usageCard');
  card.classList.toggle('open');
}

// ── Search / filter ──────────────────────────────────────────────
function filterApis(q){
  q = q.toLowerCase().trim();
  document.querySelectorAll('.api-card').forEach(card=>{
    const tags = card.dataset.tags || '';
    const path = card.querySelector('.api-path')?.textContent || '';
    const desc = card.querySelector('.api-desc-short')?.textContent || '';
    const match = !q || tags.includes(q) || path.includes(q) || desc.toLowerCase().includes(q);
    card.style.display = match ? '' : 'none';
  });
  document.querySelectorAll('.section-title').forEach(sec=>{
    let el = sec.nextElementSibling;
    let hasVisible = false;
    while(el && !el.classList.contains('section-title')){
      if(el.classList.contains('api-card') && el.style.display !== 'none') hasVisible = true;
      el = el.nextElementSibling;
    }
    sec.style.display = hasVisible ? '' : 'none';
  });
}

// Open first card by default
document.querySelector('.api-card')?.classList.add('open');
</script>
</body>
</html>"""


@app.route("/api")
def api_docs():
    """API Documentation page."""
    base = request.host_url.rstrip("/")
    html = _API_DOCS_HTML.replace("https://yourbot.replit.dev", base)
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/api/docs")
def api_docs_alias():
    return api_docs()


if __name__ == "__main__":
    port = int(os.environ.get("WEB_PORT") or 5000)
    from ANNIEMUSIC.utils.weburl import WEB_URL
    if WEB_URL:
        print(f"[AnnieXMusic Web] 🎵 Player URL: {WEB_URL}")
        print("[AnnieXMusic Web] ✅ Mini App button will auto-appear in /start and play messages")
    else:
        print("[AnnieXMusic Web] ⚠️  No WEB_APP_URL detected. Set WEB_APP_URL env var for Mini App buttons.")
    app.run(host="0.0.0.0", port=port, debug=False)
