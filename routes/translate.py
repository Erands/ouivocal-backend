from flask import Blueprint, request, jsonify
import os
import uuid
from concurrent.futures import ThreadPoolExecutor

from services.audio_service import transcribe_audio
from services.translation_service import do_translate
from services.voice_service import create_voice

translate_bp = Blueprint("translate", __name__)

# 🔥 THREAD POOL (FAST)
executor = ThreadPoolExecutor(max_workers=3)

# 📁 FOLDERS
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# 🔗 YOUR BACKEND URL (IMPORTANT)
BASE_URL = "https://ouivocal-api.onrender.com"


# =========================
# TEXT TRANSLATION (FAST)
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

        # 🔥 TRANSLATE FIRST (FAST)
        translated = do_translate(text, direction)

        # 🔥 GENERATE AUDIO FILE
        filename = f"{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(OUTPUT_FOLDER, filename)

        audio_file = create_voice(translated, direction, gender, output_path)

        # 🔥 RETURN FULL URL
        audio_url = f"{BASE_URL}/audio/{filename}" if audio_file else None

        return jsonify({
            "translated": translated,
            "audio": audio_url
        })

    except Exception as e:
        print("Text error:", e)
        return jsonify({"error": "Translation failed"}), 500


# =========================
# AUDIO TRANSLATION (NORMAL MODE)
# =========================
@translate_bp.route("/audio", methods=["POST"])
def translate_audio():
    try:
        audio_file = request.files.get("audio")
        direction = request.form.get("direction")
        gender = request.form.get("gender", "female")

        if not audio_file:
            return jsonify({"error": "No audio file"}), 400

        # 💾 SAVE AUDIO
        filename = f"{uuid.uuid4().hex}.webm"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        audio_file.save(filepath)

        # 🎧 TRANSCRIBE
        text = transcribe_audio(filepath, direction)

        if not text or "No speech" in text:
            return jsonify({
                "translated": "⚠️ No speech detected",
                "audio": None
            })

        # 🌍 TRANSLATE
        translated = do_translate(text, direction)

        # 🔊 CREATE AUDIO
        out_name = f"{uuid.uuid4().hex}.mp3"
        out_path = os.path.join(OUTPUT_FOLDER, out_name)

        audio_file = create_voice(translated, direction, gender, out_path)

        audio_url = f"{BASE_URL}/audio/{out_name}" if audio_file else None

        return jsonify({
            "original": text,
            "translated": translated,
            "audio": audio_url
        })

    except Exception as e:
        print("Audio error:", e)
        return jsonify({"error": "Audio failed"}), 500


# =========================
# ⚡ LIVE MODE (ULTRA FAST - NO AUDIO)
# =========================
@translate_bp.route("/audio-live", methods=["POST"])
def translate_audio_live():
    try:
        audio_file = request.files.get("audio")
        direction = request.form.get("direction")

        if not audio_file:
            return jsonify({"translated": ""})

        # 💾 SAVE SMALL CHUNK
        filename = f"{uuid.uuid4().hex}.webm"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        audio_file.save(filepath)

        # 🎧 TRANSCRIBE (FAST MODEL)
        text = transcribe_audio(filepath, direction)

        if not text:
            return jsonify({"translated": ""})

        # 🌍 TRANSLATE ONLY (NO VOICE = FAST)
        translated = do_translate(text, direction)

        return jsonify({
            "original": text,
            "translated": translated
        })

    except Exception as e:
        print("Live error:", e)
        return jsonify({"translated": ""})