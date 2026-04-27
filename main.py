from flask import Flask, send_from_directory
from flask_cors import CORS
from routes.translate import translate_bp
import os

app = Flask(__name__)
CORS(app)

# 🔥 FOLDERS (VERY IMPORTANT)
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# =========================
# REGISTER ROUTES
# =========================
app.register_blueprint(translate_bp)

# =========================
# AUDIO SERVE ROUTE (FIXED POSITION)
# =========================
@app.route("/audio/<path:filename>")
def serve_audio(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

# =========================
# HOME ROUTE
# =========================
@app.route("/")
def home():
    return "OuiVocal API Running 🚀"

# =========================
# PORT (RENDER COMPATIBLE)
# =========================
PORT = int(os.environ.get("PORT", 10000))

# =========================
# START SERVER
# =========================
if __name__ == "__main__":
    print(f"🚀 Starting Flask on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)

    app = Flask(__name__)
app.config["DEBUG"] = True   # 🔥 ADD THIS LINE
CORS(app)