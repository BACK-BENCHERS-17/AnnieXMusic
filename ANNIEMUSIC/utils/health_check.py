import threading
import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health_check():
    return 'Bot is alive!', 200

def start_health_server():
    port = int(os.environ.get('PORT', 8080))
    # Use 0.0.0.0 to be accessible from outside the container
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
