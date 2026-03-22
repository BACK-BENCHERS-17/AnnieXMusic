import os
import time
import threading
import psutil
import yt_dlp
from flask import Flask, jsonify, send_from_directory, request, Response
import requests

WEB_DIR = os.path.join(os.path.dirname(__file__), 'ANNIEMUSIC', 'utils', 'web')
app = Flask(__name__)
_boot_time = time.time()

# ── Trending cache ──────────────────────────────────────────────
_trending_cache = {"data": [], "ts": 0}
_CACHE_TTL = 1800  # 30 min

TRENDING_QUERIES = [
    ("Bollywood Hits 2025", "ytsearch10:bollywood hits trending 2025"),
    ("International", "ytsearch10:top hits 2025 pop"),
    ("Punjabi", "ytsearch10:punjabi songs trending 2025"),
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
                        "id": vid,
                        "title": e.get("title", "Unknown"),
                        "channel": e.get("channel") or e.get("uploader", ""),
                        "duration": e.get("duration_string") or _sec_to_min(e.get("duration", 0)),
                        "thumb": f"https://img.youtube.com/vi/{vid}/mqdefault.jpg",
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
        chats_data.append({
            "chat_id": chat_id,
            "current": {
                "title": cur.get("title", "Unknown"),
                "duration": cur.get("dur", "0:00"),
                "played": cur.get("played", 0),
                "seconds": cur.get("seconds", 0),
                "by": cur.get("by", "Unknown"),
                "streamtype": cur.get("streamtype", "youtube"),
                "vidid": vid,
                "thumbnail": thumb,
            },
            "queue_count": max(len(queue) - 1, 0),
            "queue": [
                {
                    "title": t.get("title", "Unknown"),
                    "duration": t.get("dur", "0:00"),
                    "by": t.get("by", "Unknown"),
                    "vidid": str(t.get("vidid", "")),
                    "thumb": f"https://img.youtube.com/vi/{str(t.get('vidid',''))}/default.jpg"
                           if len(str(t.get("vidid", ""))) == 11 else "",
                }
                for t in queue[1:8]
            ],
        })

    try:
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory()
        ram_used = f"{ram.used // (1024**2)} MB"
        ram_total = f"{ram.total // (1024**2)} MB"
        ram_pct = round(ram.percent, 1)
    except Exception:
        cpu, ram_used, ram_total, ram_pct = 0, "N/A", "N/A", 0

    up = int(time.time() - boot_time)
    h, rem = divmod(up, 3600)
    m, s = divmod(rem, 60)

    return jsonify({
        "status": "online",
        "uptime": f"{h}h {m}m {s}s",
        "active_chats": len(chats_data),
        "cpu": cpu,
        "ram_used": ram_used,
        "ram_total": ram_total,
        "ram_percent": ram_pct,
        "chats": chats_data,
    })

@app.route("/api/trending")
def api_trending():
    data = get_trending()
    return jsonify({"songs": data, "cached": bool(data)})

@app.route("/api/stream")
def api_stream():
    vid = request.args.get("v", "").strip()
    if not vid or len(vid) != 11:
        return jsonify({"error": "Invalid video id"}), 400
    try:
        ydl_opts = {
            "quiet": True, "no_warnings": True,
            "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
            "skip_download": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
            if not info:
                return jsonify({"error": "Could not fetch stream"}), 500
            url = info.get("url", "")
            title = info.get("title", "Unknown")
            channel = info.get("channel") or info.get("uploader", "")
            dur = info.get("duration", 0)
            thumb = f"https://img.youtube.com/vi/{vid}/mqdefault.jpg"
            return jsonify({
                "url": url,
                "title": title,
                "channel": channel,
                "duration": _sec_to_min(dur),
                "seconds": dur,
                "thumb": thumb,
            })
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
                    "id": vid,
                    "title": e.get("title", "Unknown"),
                    "channel": e.get("channel") or e.get("uploader", ""),
                    "duration": e.get("duration_string") or _sec_to_min(e.get("duration", 0)),
                    "thumb": f"https://img.youtube.com/vi/{vid}/mqdefault.jpg",
                })
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e), "results": []}), 500

@app.route("/api/health")
def health():
    return jsonify({"status": "alive"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("WEB_PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
