import os
import sys
import time
import threading
import psutil
from flask import Flask, jsonify, send_from_directory

WEB_DIR = os.path.join(os.path.dirname(__file__), 'ANNIEMUSIC', 'utils', 'web')

app = Flask(__name__)

_boot_time = time.time()

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

    active_chats_data = []
    for chat_id, queue in db.items():
        if not queue:
            continue
        current = queue[0]
        vidid = current.get("vidid", "")
        thumb = ""
        if vidid and len(str(vidid)) == 11:
            thumb = f"https://img.youtube.com/vi/{vidid}/hqdefault.jpg"
        active_chats_data.append({
            "chat_id": chat_id,
            "current": {
                "title": current.get("title", "Unknown"),
                "duration": current.get("dur", "0:00"),
                "played": current.get("played", 0),
                "seconds": current.get("seconds", 0),
                "by": current.get("by", "Unknown"),
                "streamtype": current.get("streamtype", "youtube"),
                "vidid": vidid,
                "thumbnail": thumb,
            },
            "queue_count": len(queue) - 1,
            "queue": [
                {
                    "title": t.get("title", "Unknown"),
                    "duration": t.get("dur", "0:00"),
                    "by": t.get("by", "Unknown"),
                    "vidid": t.get("vidid", ""),
                }
                for t in queue[1:6]
            ],
        })

    try:
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory()
        ram_used = f"{ram.used // (1024**2)} MB"
        ram_total = f"{ram.total // (1024**2)} MB"
        ram_percent = ram.percent
    except Exception:
        cpu = 0
        ram_used = "N/A"
        ram_total = "N/A"
        ram_percent = 0

    uptime_secs = int(time.time() - boot_time)
    hours, rem = divmod(uptime_secs, 3600)
    mins, secs = divmod(rem, 60)
    uptime_str = f"{hours}h {mins}m {secs}s"

    return jsonify({
        "status": "online",
        "uptime": uptime_str,
        "active_chats": len(active_chats_data),
        "cpu": cpu,
        "ram_used": ram_used,
        "ram_total": ram_total,
        "ram_percent": ram_percent,
        "chats": active_chats_data,
    })

@app.route('/api/health')
def health():
    return jsonify({"status": "alive"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('WEB_PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
