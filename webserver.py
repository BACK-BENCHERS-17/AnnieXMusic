import os
import time
import threading
import psutil
import yt_dlp
from flask import Flask, jsonify, send_from_directory, request, Response, send_file
import requests
import tempfile
import re
from urllib.parse import urlparse, parse_qs

WEB_DIR = os.path.join(os.path.dirname(__file__), 'ANNIEMUSIC', 'utils', 'web')
app = Flask(__name__)
_boot_time = time.time()

# ── Cookies helper (defined early so all yt-dlp callers can use it) ─────────
_COOKIE_PATH = os.path.join(os.path.dirname(__file__), "ANNIEMUSIC", "assets", "cookies.txt")

def _cookie_opts():
    """Return cookiefile option dict if the cookies file exists and is non-empty."""
    try:
        if os.path.isfile(_COOKIE_PATH) and os.path.getsize(_COOKIE_PATH) > 50:
            return {"cookiefile": _COOKIE_PATH}
    except Exception:
        pass
    return {}

# ── Trending cache ───────────────────────────────────────────────
_trending_cache = {"data": [], "ts": 0}
_CACHE_TTL = 1800  # 30 min

TRENDING_QUERIES = [
    ("Hindi",          "ytsearch10:hindi songs trending 2025"),
    ("Punjabi",        "ytsearch10:punjabi songs trending 2025"),
    ("Bollywood",      "ytsearch10:bollywood hits 2025"),
    ("International",  "ytsearch10:top hits 2025 pop english"),
]

def _fetch_trending():
    results = []
    ydl_opts = {
        "quiet": True, "no_warnings": True,
        "extract_flat": True, "skip_download": True,
        "ignoreerrors": True,
        **_cookie_opts(),
    }
    for category, query in TRENDING_QUERIES:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=False)
                entries = info.get("entries", []) if info else []
                for e in entries:
                    if not e:
                        continue
                    vid = e.get("id") or e.get("url", "")
                    if not vid or len(vid) != 11:
                        continue
                    results.append({
                        "id":       vid,
                        "title":    e.get("title", "Unknown"),
                        "channel":  e.get("channel") or e.get("uploader", ""),
                        "duration": e.get("duration_string") or _sec_to_min(e.get("duration", 0)),
                        "thumb":    f"https://img.youtube.com/vi/{vid}/mqdefault.jpg",
                        "category": category,
                    })
        except Exception:
            pass
    return results

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

def _sec_to_min(s):
    if not s:
        return "0:00"
    s = int(s)
    return f"{s // 60}:{s % 60:02d}"

# Start trending prefetch in background on startup
threading.Thread(target=get_trending, daemon=True).start()

# ── Stream URL cache (avoids double yt-dlp calls) ───────────────
_stream_cache = {}
_stream_lock  = threading.Lock()

def _url_expire_ts(url):
    """Extract YouTube's 'expire' unix timestamp from a signed URL, or None."""
    try:
        qs = parse_qs(urlparse(url).query)
        exp = qs.get("expire", [None])[0]
        if exp:
            return int(exp)
    except Exception:
        pass
    return None

def _is_url_valid(data):
    """Return True if the cached stream URL is still valid (not near expiry)."""
    exp = _url_expire_ts(data.get("url", ""))
    if exp:
        # Treat URL as invalid if it expires within the next 5 minutes
        return time.time() < exp - 300
    # Fallback: trust cache for 8 minutes if no expire param found
    return time.time() - data.get("ts", 0) < 480

# Format attempts in order — try best audio first, fall back to anything streamable
_FORMAT_ATTEMPTS = [
    "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
    "bestaudio/best",
    "best",
]

def _fetch_stream_data(vid):
    """Call yt-dlp to get a fresh stream URL for the given video ID (with cookies + retry)."""
    url = f"https://www.youtube.com/watch?v={vid}"
    base_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        **_cookie_opts(),
    }

    info = None
    for fmt in _FORMAT_ATTEMPTS:
        try:
            opts = {**base_opts, "format": fmt}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            if info and info.get("url"):
                break
            info = None
        except Exception:
            info = None
            continue

    if not info or not info.get("url"):
        return None

    stream_url = info["url"]
    data = {
        "url":      stream_url,
        "ext":      info.get("ext", "m4a"),
        "title":    info.get("title", "Unknown"),
        "channel":  info.get("channel") or info.get("uploader", ""),
        "duration": _sec_to_min(info.get("duration", 0)),
        "seconds":  info.get("duration", 0),
        "thumb":    f"https://img.youtube.com/vi/{vid}/mqdefault.jpg",
        "ts":       time.time(),
    }
    with _stream_lock:
        _stream_cache[vid] = data
    return data

def _get_stream_data(vid, force_refresh=False):
    """Return cached stream data if still valid, otherwise fetch fresh."""
    if not force_refresh:
        with _stream_lock:
            cached = _stream_cache.get(vid)
        if cached and _is_url_valid(cached):
            return cached
    return _fetch_stream_data(vid)

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

@app.route("/api/stream")
def api_stream():
    """Return metadata for a video (no stream URL exposed to browser)."""
    vid = request.args.get("v", "").strip()
    if not vid or len(vid) != 11:
        return jsonify({"error": "Invalid video id"}), 400
    try:
        data = _get_stream_data(vid)
        if not data:
            return jsonify({"error": "Could not fetch stream"}), 500
        return jsonify({
            "title":    data["title"],
            "channel":  data["channel"],
            "duration": data["duration"],
            "seconds":  data["seconds"],
            "thumb":    data["thumb"],
        })
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
        if upstream is None:
            return jsonify({"error": "Could not fetch stream"}), 500

        # If YouTube rejects the cached URL (expired), fetch a fresh one and retry once
        if upstream.status_code in (400, 403, 410):
            upstream.close()
            upstream, content_type = _proxy_audio(vid, force_refresh=True)
            if upstream is None:
                return jsonify({"error": "Could not refresh stream"}), 500

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

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"results": []})
    try:
        ydl_opts = {
            "quiet": True, "no_warnings": True,
            "extract_flat": True, "skip_download": True,
            "ignoreerrors": True,
            **_cookie_opts(),
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch8:{q}", download=False)
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
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e), "results": []}), 500

@app.route("/api/download")
def api_download():
    """Download audio file via yt-dlp and send to browser."""
    vid = request.args.get("v", "").strip()
    if not vid or len(vid) != 11:
        return jsonify({"error": "Invalid video id"}), 400
    try:
        tmp_dir = tempfile.mkdtemp()
        out_template = os.path.join(tmp_dir, "%(title)s.%(ext)s")
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
            "outtmpl": out_template,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
            }],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=True)
            title = info.get("title", vid)
            # Find the downloaded file
            safe_title = re.sub(r'[^\w\s\-\.]', '', title)[:80]
            files = [f for f in os.listdir(tmp_dir) if os.path.isfile(os.path.join(tmp_dir, f))]
            if not files:
                return jsonify({"error": "Download failed"}), 500
            filepath = os.path.join(tmp_dir, files[0])
            ext = os.path.splitext(files[0])[1].lstrip('.')
            mime = "audio/mp4" if ext in ("m4a", "mp4") else f"audio/{ext}"
            filename = f"{safe_title}.{ext}"
            return send_file(
                filepath,
                mimetype=mime,
                as_attachment=True,
                download_name=filename,
            )
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

@app.route("/api/health")
def health():
    return jsonify({"status": "alive"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT") or os.environ.get("WEB_PORT") or 5000)
    from ANNIEMUSIC.utils.weburl import WEB_URL
    if WEB_URL:
        print(f"[AnnieXMusic Web] 🎵 Player URL: {WEB_URL}")
        print("[AnnieXMusic Web] ✅ Mini App button will auto-appear in /start and play messages")
    else:
        print("[AnnieXMusic Web] ⚠️  No WEB_APP_URL detected. Set WEB_APP_URL env var for Mini App buttons.")
    app.run(host="0.0.0.0", port=port, debug=False)
