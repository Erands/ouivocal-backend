from flask import Blueprint, request, jsonify
import os
import uuid
from concurrent.futures import ThreadPoolExecutor

from services.audio_service import transcribe_audio
from services.translation_service import do_translate
from services.voice_service import create_voice

translate_bp = Blueprint("translate", __name__)

# 🔥 Thread pool for parallel processing
executor = ThreadPoolExecutor(max_workers=3)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================
# TEXT TRANSLATION
# =========================
@translate_bp.route("/translate", methods=["POST"])
def translate_text():
    data = request.json

    text = data.get("text")
    direction = data.get("direction")
    gender = data.get("gender", "female")

    if not text:
        return jsonify({"error": "No text provided"}), 400

    try:
        # 🔥 Run translation + voice in parallel
        future_translate = executor.submit(do_translate, text, direction)
        future_voice = executor.submit(create_voice, text, direction, gender)

        translated = future_translate.result()
        audio = future_voice.result()

        return jsonify({
            "translated": translated,
            "audio": audio
        })

    except Exception as e:
        print("Error:", e)
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

        filename = f"{uuid.uuid4().hex}.webm"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        audio_file.save(filepath)

        # 1️⃣ Transcribe first
        text = transcribe_audio(filepath, direction)

        if not text or "No speech" in text:
            return jsonify({
                "translated": "⚠️ No speech detected",
                "audio": None
            })

        # 2️⃣ Parallel translate + voice
        future_translate = executor.submit(do_translate, text, direction)
        future_voice = executor.submit(create_voice, text, direction, gender)

        translated = future_translate.result()
        audio = future_voice.result()

        return jsonify({
            "original": text,
            "translated": translated,
            "audio": audio
        })

    except Exception as e:
        print("Audio error:", e)
        return jsonify({"error": "Audio failed"}), 500