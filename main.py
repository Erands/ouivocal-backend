from flask import Flask
from flask_cors import CORS
from routes.translate import translate_bp
import os

app = Flask(__name__)
CORS(app)

# =========================
# REGISTER ROUTES
# =========================
app.register_blueprint(translate_bp)

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