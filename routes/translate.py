from flask import Blueprint, request, jsonify
import os
import uuid
from concurrent.futures import ThreadPoolExecutor

from services.audio_service import transcribe_audio
from services.translation_service import do_translate
from services.voice_service import create_voice

translate_bp = Blueprint("translate", __name__)

# 🔥 Thread pool (optimized)
executor = ThreadPoolExecutor(max_workers=3)

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
            return jsonify({"error": "No text provided"}), 400

        # 🔥 Step 1: Translate (FAST)
        translated = do_translate(text, direction)

        # 🔥 Step 2: Generate audio file
        filename = f"{uuid.uuid4().hex}.mp3"
        audio_path = os.path.join(OUTPUT_FOLDER, filename)

        audio_file = create_voice(translated, direction, gender, audio_path)

        # 🔥 Step 3: Return safe response
        audio_url = None
        if audio_file:
            audio_url = f"/audio/{filename}"

        return jsonify({
            "translated": translated,
            "audio": audio_url
        })

    except Exception as e:
        print("❌ Text error:", e)
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

        # 🔥 Save uploaded file
        filename = f"{uuid.uuid4().hex}.webm"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        audio_file.save(filepath)

        # 🔥 Step 1: Transcribe
        text = transcribe_audio(filepath, direction)

        if not text or "No speech" in text:
            return jsonify({
                "translated": "⚠️ No speech detected",
                "audio": None
            })

        # 🔥 Step 2: Translate
        translated = do_translate(text, direction)

        # 🔥 Step 3: Generate voice
        out_name = f"{uuid.uuid4().hex}.mp3"
        audio_path = os.path.join(OUTPUT_FOLDER, out_name)

        audio_file = create_voice(translated, direction, gender, audio_path)

        audio_url = None
        if audio_file:
            audio_url = f"/audio/{out_name}"

        return jsonify({
            "original": text,
            "translated": translated,
            "audio": audio_url
        })

    except Exception as e:
        print("❌ Audio error:", e)
        return jsonify({"error": "Audio failed"}), 500