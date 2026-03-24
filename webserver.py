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


@app.route("/api/ytdl")
def api_ytdl():
    """
    Internal API: download YouTube audio to local MP3 file.
    Protected by internal random key — only the bot (same process) should call this.
    GET /api/ytdl?v=VIDEO_ID&key=INTERNAL_KEY
    Returns: {"path": "/abs/path/to/VIDEO_ID.mp3"}
    """
    vid = request.args.get("v", "").strip()
    key = request.args.get("key", "").strip()

    if not vid or len(vid) != 11:
        return jsonify({"error": "Invalid video id"}), 400
    if key != _INTERNAL_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    out_path = os.path.join(_DOWNLOAD_DIR, f"{vid}.mp3")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 1024:
        return jsonify({"path": out_path, "cached": True})

    with _ytdl_lock_guard:
        if vid not in _ytdl_locks:
            _ytdl_locks[vid] = threading.Lock()
        vid_lock = _ytdl_locks[vid]

    with vid_lock:
        if os.path.exists(out_path) and os.path.getsize(out_path) > 1024:
            return jsonify({"path": out_path, "cached": True})

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
            if os.path.exists(out_path) and os.path.getsize(out_path) > 1024:
                return jsonify({"path": out_path})
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
    """
    data = _get_stream_data(vid, force_refresh=force_refresh)
    if not data:
        return None, None

    stream_url = data["url"]
    ext = data.get("ext", "m4a")
    content_type = "audio/mp4" if ext == "m4a" else f"audio/{ext}"

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
    return upstream, content_type


@app.route("/api/audio")
def api_audio():
    """Proxy audio stream from YouTube — avoids browser CORS issues."""
    vid = request.args.get("v", "").strip()
    if not vid or len(vid) != 11:
        return jsonify({"error": "Invalid video id"}), 400
    try:
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

        # Fallback: download audio locally and serve from disk
        # (handles Railway/cloud IPs blocked by YouTube bot detection)
        if upstream is not None:
            try:
                upstream.close()
            except Exception:
                pass
        file_path = _download_audio_local(vid)
        if file_path is None:
            return jsonify({"error": "Could not fetch audio"}), 500
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

if __name__ == "__main__":
    port = int(os.environ.get("WEB_PORT") or 5000)
    from ANNIEMUSIC.utils.weburl import WEB_URL
    if WEB_URL:
        print(f"[AnnieXMusic Web] 🎵 Player URL: {WEB_URL}")
        print("[AnnieXMusic Web] ✅ Mini App button will auto-appear in /start and play messages")
    else:
        print("[AnnieXMusic Web] ⚠️  No WEB_APP_URL detected. Set WEB_APP_URL env var for Mini App buttons.")
    app.run(host="0.0.0.0", port=port, debug=False)
