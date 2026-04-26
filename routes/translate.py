from flask import Blueprint, request, jsonify
import os
import uuid
from concurrent.futures import ThreadPoolExecutor

from services.audio_service import transcribe_audio
from services.translation_service import do_translate
from services.voice_service import create_voice

translate_bp = Blueprint("translate", __name__)

# 🔥 Thread pool (faster processing)
executor = ThreadPoolExecutor(max_workers=3)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

OUTPUT_FOLDER = "outputs"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# 🔥 IMPORTANT (YOUR BACKEND DOMAIN)
BASE_URL = os.environ.get("BASE_URL", "https://ouivocal-api.onrender.com")


# =========================
# TEXT TRANSLATION
# =========================
@translate_bp.route("/translate", methods=["POST"])
def translate_text():
    try:
        data = request.json

        text = data.get("text")
        direction = data.get("direction")
        gender = data.get("gender", "female")

        if not text:
            return jsonify({"error": "No text provided"}), 400

        # 🔥 1. TRANSLATE FIRST (FAST)
        translated = do_translate(text, direction)

        # 🔥 2. GENERATE VOICE (AFTER TRANSLATION)
        audio_filename = create_voice(translated, direction, gender)

        # 🔥 3. BUILD FULL URL
        audio_url = f"{BASE_URL}/audio/{audio_filename}" if audio_filename else None

        return jsonify({
            "translated": translated,
            "audio": audio_url
        })

    except Exception as e:
        print("❌ TEXT ERROR:", e)
        return jsonify({"error": "Translation failed"}), 500


# =========================
# AUDIO TRANSLATION
# =========================
@translate_bp.route("/audio", methods=["POST"])
def translate_audio():
    try:
        audio_file = request.files.get("audio")
        direction = request.form.get("direction")
        gender = request.form.get("gender", "female")

        if not audio_file:
            return jsonify({"error": "No audio file"}), 400

        # 🔥 SAVE INPUT AUDIO
        filename = f"{uuid.uuid4().hex}.webm"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        audio_file.save(filepath)

        # 🔥 1. TRANSCRIBE
        text = transcribe_audio(filepath, direction)

        if not text or "No speech" in text:
            return jsonify({
                "translated": "⚠️ No speech detected",
                "audio": None
            })

        # 🔥 2. TRANSLATE
        translated = do_translate(text, direction)

        # 🔥 3. GENERATE VOICE
        audio_filename = create_voice(translated, direction, gender)

        # 🔥 4. BUILD FULL URL
        audio_url = f"{BASE_URL}/audio/{audio_filename}" if audio_filename else None

        return jsonify({
            "original": text,
            "translated": translated,
            "audio": audio_url
        })

    except Exception as e:
        print("❌ AUDIO ERROR:", e)
        return jsonify({"error": "Audio failed"}), 500