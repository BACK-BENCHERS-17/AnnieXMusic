import os
import time
import threading
import psutil
import yt_dlp
from flask import Flask, jsonify, send_from_directory, request, Response, send_file
import requests
import re
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout

_BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

WEB_DIR = os.path.join(os.path.dirname(__file__), 'ANNIEMUSIC', 'utils', 'web')
app = Flask(__name__)
_boot_time = time.time()

def _sec_to_min(s):
    if not s:
        return "0:00"
    s = int(s)
    return f"{s // 60}:{s % 60:02d}"

# ── Piped API instances (tried in order, fastest & no cookies needed) ────────
_PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://api.piped.privacydev.net",
    "https://piped-api.garudalinux.org",
    "https://api.piped.projectsegfau.lt",
    "https://watchapi.whatever.social",
]

# ── Invidious API instances (second fallback) ─────────────────────────────────
_INVIDIOUS_INSTANCES = [
    "https://invidious.io.lol",
    "https://invidious.nerdvpn.de",
    "https://yt.artemislena.eu",
    "https://invidious.privacydev.net",
    "https://vid.puffyan.us",
]

_API_TIMEOUT = 5  # seconds per instance

def _best_audio_from_piped(streams):
    """Pick highest-bitrate m4a stream, fallback to any audio stream."""
    if not streams:
        return None, None
    m4a = [s for s in streams if "mp4" in s.get("mimeType", "") or "m4a" in s.get("mimeType", "")]
    pool = m4a if m4a else streams
    best = max(pool, key=lambda s: s.get("bitrate", 0))
    ext = "m4a" if "mp4" in best.get("mimeType", "") else "webm"
    return best.get("url"), ext

def _fetch_via_piped(vid):
    """Try each Piped instance to get a stream URL. Returns data dict or None."""
    for base in _PIPED_INSTANCES:
        try:
            r = requests.get(f"{base}/streams/{vid}", timeout=_API_TIMEOUT)
            if r.status_code != 200:
                continue
            d = r.json()
            stream_url, ext = _best_audio_from_piped(d.get("audioStreams", []))
            if not stream_url:
                continue
            dur = int(d.get("duration", 0))
            return {
                "url":      stream_url,
                "ext":      ext,
                "title":    d.get("title", "Unknown"),
                "channel":  d.get("uploader", ""),
                "duration": _sec_to_min(dur),
                "seconds":  dur,
                "thumb":    f"https://img.youtube.com/vi/{vid}/mqdefault.jpg",
                "ts":       time.time(),
            }
        except Exception:
            continue
    return None

def _best_audio_from_invidious(formats):
    """Pick best audio adaptive format from Invidious."""
    audio = [f for f in formats if f.get("type", "").startswith("audio")]
    if not audio:
        return None, None
    m4a = [f for f in audio if "mp4" in f.get("type", "") or f.get("container") == "m4a"]
    pool = m4a if m4a else audio
    best = max(pool, key=lambda f: int(f.get("bitrate", 0)))
    ext = "m4a" if "mp4" in best.get("type", "") else "webm"
    return best.get("url"), ext

def _fetch_via_invidious(vid):
    """Try each Invidious instance. Returns data dict or None."""
    for base in _INVIDIOUS_INSTANCES:
        try:
            r = requests.get(
                f"{base}/api/v1/videos/{vid}",
                params={"fields": "adaptiveFormats,title,author,lengthSeconds"},
                timeout=_API_TIMEOUT,
            )
            if r.status_code != 200:
                continue
            d = r.json()
            stream_url, ext = _best_audio_from_invidious(d.get("adaptiveFormats", []))
            if not stream_url:
                continue
            dur = int(d.get("lengthSeconds", 0))
            return {
                "url":      stream_url,
                "ext":      ext,
                "title":    d.get("title", "Unknown"),
                "channel":  d.get("author", ""),
                "duration": _sec_to_min(dur),
                "seconds":  dur,
                "thumb":    f"https://img.youtube.com/vi/{vid}/mqdefault.jpg",
                "ts":       time.time(),
            }
        except Exception:
            continue
    return None

def _fetch_via_ytdlp(vid):
    """yt-dlp extraction — no cookies, optimised for speed (~3s)."""
    try:
        opts = {
            "quiet": True, "no_warnings": True,
            "skip_download": True,
            # format 140 = m4a 128kbps, always present → no format negotiation needed
            "format": "140/bestaudio[ext=m4a]/bestaudio/best",
            "extractor_args": {"youtube": {"skip": ["hls", "dash", "translated_subs"]}},
            "socket_timeout": 12,
            "retries": 1,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
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

# ── Stream cache ─────────────────────────────────────────────────────────────
_stream_cache = {}
_stream_lock  = threading.Lock()

def _url_expire_ts(url):
    try:
        exp = parse_qs(urlparse(url).query).get("expire", [None])[0]
        return int(exp) if exp else None
    except Exception:
        return None

def _is_url_valid(data):
    exp = _url_expire_ts(data.get("url", ""))
    if exp:
        return time.time() < exp - 300   # expire 5 min early
    return time.time() - data.get("ts", 0) < 3600  # 1-hour fallback for API URLs

def _fetch_stream_data(vid):
    """
    Race Piped, Invidious, and yt-dlp in parallel.
    Returns the first successful result without waiting for the rest.
    Fastest source wins — Piped < 1s when available, yt-dlp ~3s reliable fallback.
    """
    executor = ThreadPoolExecutor(max_workers=3)
    futures = [
        executor.submit(_fetch_via_piped, vid),
        executor.submit(_fetch_via_invidious, vid),
        executor.submit(_fetch_via_ytdlp, vid),
    ]
    data = None
    try:
        for future in as_completed(futures, timeout=20):
            try:
                result = future.result()
                if result:
                    data = result
                    break
            except Exception:
                continue
    except FuturesTimeout:
        pass
    finally:
        # Shutdown without waiting — remaining tasks finish in background
        executor.shutdown(wait=False)
    if data:
        with _stream_lock:
            _stream_cache[vid] = data
    return data

def _get_stream_data(vid, force_refresh=False):
    if not force_refresh:
        with _stream_lock:
            cached = _stream_cache.get(vid)
        if cached and _is_url_valid(cached):
            return cached
    return _fetch_stream_data(vid)

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
    Protected by BOT_TOKEN — only the bot (same Railway service) can call this.
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
        return jsonify({"results": results})
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
    """Fetch best video+audio stream URL via yt-dlp for video playback."""
    try:
        opts = {
            "quiet": True, "no_warnings": True,
            "skip_download": True,
            "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[ext=mp4]/best",
            "merge_output_format": "mp4",
            "extractor_args": {"youtube": {"skip": ["hls", "translated_subs"]}},
            "socket_timeout": 15,
            "retries": 1,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
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
