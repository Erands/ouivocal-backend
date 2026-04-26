from flask import Flask
from flask_cors import CORS
from routes.translate import translate_bp

import asyncio
import websockets
import threading
import os

from realtime.call_ws import handler

app = Flask(__name__)
CORS(app)

app.register_blueprint(translate_bp)

@app.route("/")
def home():
    return "OuiVocal API Running 🚀"


# ✅ GET PORT FROM RENDER
PORT = int(os.environ.get("PORT", 5000))


# 🔥 RUN WEBSOCKET ON SAME PORT
async def start_ws():
    async with websockets.serve(
        handler,
        "0.0.0.0",
        PORT,   # SAME PORT
        ping_interval=20,
        ping_timeout=60,
        max_size=None
    ):
        print(f"🚀 WebSocket running on port {PORT}")
        await asyncio.Future()  # run forever


def run_ws():
    asyncio.run(start_ws())


if __name__ == "__main__":
    # Start WebSocket in background
    threading.Thread(target=run_ws, daemon=True).start()

    # Start Flask
    app.run(host="0.0.0.0", port=PORT)