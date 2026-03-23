import os
import re
import time
import tempfile
import threading
import psutil
import yt_dlp
import requests
from urllib.parse import urlparse, parse_qs
from flask import Flask, jsonify, send_from_directory, request, Response, send_file

app = Flask(__name__)

_BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
_boot_time = time.time()

WEB_DIR = os.path.join(os.path.dirname(__file__), 'web')
_DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'downloads')
os.makedirs(_DOWNLOAD_DIR, exist_ok=True)
_ytdl_locks: dict = {}
_ytdl_lock_guard = threading.Lock()

# ── YT-DLP no-cookie options (android_vr works on cloud/Replit without cookies) ──
_YDL_AUDIO_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
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


def _sec_to_min(s):
    if not s:
        return "0:00"
    s = int(s)
    return f"{s // 60}:{s % 60:02d}"


def _url_still_valid(data):
    try:
        exp = parse_qs(urlparse(data.get("url", "")).query).get("expire", [None])[0]
        if exp:
            return time.time() < int(exp) - 300
    except Exception:
        pass
    return time.time() - data.get("ts", 0) < 3600


def _fetch_stream(vid):
    """Fetch YouTube stream URL using android_vr client — no cookies needed."""
    url_str = f"https://www.youtube.com/watch?v={vid}"
    try:
        with yt_dlp.YoutubeDL(_YDL_AUDIO_OPTS) as ydl:
            info = ydl.extract_info(url_str, download=False)
        if not info or not info.get("url"):
            return None
        dur = int(info.get("duration", 0))
        return {
            "url":      info["url"],
            "ext":      info.get("ext", "m4a"),
            "title":    info.get("title", "Unknown"),
            "channel":  info.get("channel") or info.get("uploader", ""),
            "duration": _sec_to_min(dur),
            "seconds":  dur,
            "thumb":    f"https://img.youtube.com/vi/{vid}/mqdefault.jpg",
            "ts":       time.time(),
        }
    except Exception:
        return None


# ── Trending cache ───────────────────────────────────────────────
_trending_cache = {"data": [], "ts": 0}
_CACHE_TTL = 1800

TRENDING_QUERIES = [
    ("Hindi",         "ytsearch10:hindi songs trending 2025"),
    ("Punjabi",       "ytsearch10:punjabi songs trending 2025"),
    ("Bollywood",     "ytsearch10:bollywood hits 2025"),
    ("International", "ytsearch10:top hits 2025 pop english"),
]


def _fetch_trending():
    results = []
    ydl_opts = {
        "quiet": True, "no_warnings": True,
        "extract_flat": True, "skip_download": True,
        "ignoreerrors": True,
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


# ── Stream URL cache ─────────────────────────────────────────────
_stream_cache = {}
_stream_lock  = threading.Lock()


def _get_stream_data(vid, force_refresh=False):
    if not force_refresh:
        with _stream_lock:
            cached = _stream_cache.get(vid)
        if cached and _url_still_valid(cached):
            return cached
    data = _fetch_stream(vid)
    if data:
        with _stream_lock:
            _stream_cache[vid] = data
    return data


# ── Routes ───────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory(WEB_DIR, 'index.html')


@app.route('/api/status')
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

    up = int(time.time() - boot_time)
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


@app.route('/api/trending')
def api_trending():
    data = get_trending()
    return jsonify({"songs": data, "cached": bool(data)})


@app.route('/api/yturl')
def api_yturl():
    """
    Internal bot API: returns stream URL for a YouTube video.
    Uses android_vr client — no cookies required.
    GET /api/yturl?v=VIDEO_ID&key=BOT_TOKEN
    """
    vid = request.args.get("v", "").strip()
    key = request.args.get("key", "").strip()

    if not vid or len(vid) != 11:
        return jsonify({"error": "Invalid video id"}), 400

    if _BOT_TOKEN and key != _BOT_TOKEN:
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


@app.route('/api/stream')
def api_stream():
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


@app.route('/api/audio')
def api_audio():
    """Proxy audio stream — fetches from YouTube CDN and streams to browser."""
    vid = request.args.get("v", "").strip()
    if not vid or len(vid) != 11:
        return jsonify({"error": "Invalid video id"}), 400
    try:
        data = _get_stream_data(vid)
        if not data:
            return jsonify({"error": "Could not fetch stream"}), 500

        stream_url = data["url"]
        ext = data.get("ext", "m4a")
        content_type = "audio/mp4" if ext in ("m4a", "mp4") else f"audio/{ext}"

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
            data = _get_stream_data(vid, force_refresh=True)
            if not data:
                return jsonify({"error": "Could not refresh stream"}), 500
            stream_url = data["url"]
            upstream = requests.get(stream_url, headers=req_headers, stream=True, timeout=30)

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


@app.route('/api/search')
def api_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"results": []})
    try:
        ydl_opts = {
            "quiet": True, "no_warnings": True,
            "extract_flat": True, "skip_download": True,
            "ignoreerrors": True,
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


@app.route('/api/download')
def api_download():
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
            "extractor_args": {
                "youtube": {
                    "player_client": ["android_vr"],
                }
            },
            "nocheckcertificate": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=True)
            title = info.get("title", vid)
            safe_title = re.sub(r'[^\w\s\-\.]', '', title)[:80]
            files = [f for f in os.listdir(tmp_dir) if os.path.isfile(os.path.join(tmp_dir, f))]
            if not files:
                return jsonify({"error": "Download failed"}), 500
            filepath = os.path.join(tmp_dir, files[0])
            ext = os.path.splitext(files[0])[1].lstrip('.')
            mime = "audio/mp4" if ext in ("m4a", "mp4") else f"audio/{ext}"
            filename = f"{safe_title}.{ext}"
            return send_file(filepath, mimetype=mime, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/ytdl')
def api_ytdl():
    """
    Internal API: download YouTube audio to local MP3 file via yt-dlp.
    Protected by BOT_TOKEN — only the bot (same process) should call this.
    GET /api/ytdl?v=VIDEO_ID&key=BOT_TOKEN
    Returns: {"path": "/abs/path/to/VIDEO_ID.mp3"}
    """
    vid = request.args.get("v", "").strip()
    key = request.args.get("key", "").strip()

    if not vid or len(vid) != 11:
        return jsonify({"error": "Invalid video id"}), 400
    if _BOT_TOKEN and key != _BOT_TOKEN:
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
                    "player_client": ["android_vr"],
                    "skip": ["hls", "translated_subs"],
                }
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
            return jsonify({"error": str(e)}), 500
        finally:
            with _ytdl_lock_guard:
                _ytdl_locks.pop(vid, None)


@app.route('/api/botinfo')
def api_botinfo():
    try:
        from config import BOT_NAME, BOT_USERNAME
    except Exception:
        BOT_NAME = "Annie X Music"
        BOT_USERNAME = "ANNIEXMUSICxBOT"
    assets_dir = os.path.join(os.path.dirname(__file__), '..', 'assets')
    has_pfp  = os.path.isfile(os.path.join(assets_dir, "bot_pfp.png"))
    has_upic = os.path.isfile(os.path.join(assets_dir, "upic.png"))
    pfp_url  = "/api/botpfp" if (has_pfp or has_upic) else None
    return jsonify({
        "name":     BOT_NAME,
        "username": BOT_USERNAME,
        "pfp":      pfp_url,
        "bio":      "Advanced Telegram Music Bot — streams songs & videos into voice chats using yt-dlp for high-quality audio.",
        "features": ["YouTube", "Spotify", "Apple Music", "SoundCloud", "Telegram"],
    })


@app.route('/api/botpfp')
def api_botpfp():
    assets_dir = os.path.join(os.path.dirname(__file__), '..', 'assets')
    pfp_path  = os.path.join(assets_dir, "bot_pfp.png")
    upic_path = os.path.join(assets_dir, "upic.png")
    if os.path.isfile(pfp_path):
        return send_file(pfp_path, mimetype="image/png")
    elif os.path.isfile(upic_path):
        return send_file(upic_path, mimetype="image/png")
    return jsonify({"error": "No profile picture"}), 404


@app.route('/api/health')
def health_check():
    return jsonify({"status": "alive"}), 200


def start_health_server():
    port = int(os.environ.get('PORT', 8080))
    threading.Thread(target=get_trending, daemon=True).start()
    threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False),
        daemon=True
    ).start()
