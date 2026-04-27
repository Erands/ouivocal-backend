from flask import Blueprint, request, jsonify
import os
import uuid

from services.audio_service import transcribe_audio
from services.translation_service import do_translate
from services.voice_service import create_voice

translate_bp = Blueprint("translate", __name__)

# ✅ ensure folders exist
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


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
            return jsonify({"error": "No text"}), 400

        # 🔥 translate
        translated = do_translate(text, direction)

        # 🔥 create audio
        filename = f"{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(OUTPUT_FOLDER, filename)

        create_voice(translated, direction, gender, output_path)

        audio_url = f"https://ouivocal-api.onrender.com/audio/{filename}"

        return jsonify({
            "translated": translated,
            "audio": audio_url
        })

    except Exception as e:
        print("❌ TEXT ERROR:", e)
        return jsonify({"error": "Server failed"}), 500


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
            return jsonify({"error": "No audio"}), 400

        filename = f"{uuid.uuid4().hex}.webm"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        audio_file.save(filepath)

        # 🔥 transcribe
        text = transcribe_audio(filepath, direction)

        if not text:
            return jsonify({
                "translated": "⚠️ No speech detected",
                "audio": None
            })

        # 🔥 translate
        translated = do_translate(text, direction)

        # 🔥 create voice
        audio_filename = f"{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(OUTPUT_FOLDER, audio_filename)

        create_voice(translated, direction, gender, output_path)

        audio_url = f"https://ouivocal-api.onrender.com/audio/{audio_filename}"

        return jsonify({
            "original": text,
            "translated": translated,
            "audio": audio_url
        })

    except Exception as e:
        print("❌ AUDIO ERROR:", e)
        return jsonify({"error": "Audio failed"}), 500


# =========================
# LIVE MODE (IMPORTANT)
# =========================
@translate_bp.route("/audio-live", methods=["POST"])
def translate_audio_live():
    return translate_audio()