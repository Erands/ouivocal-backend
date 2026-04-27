from flask import Blueprint, request, jsonify
import os
import uuid
from concurrent.futures import ThreadPoolExecutor

from services.audio_service import transcribe_audio
from services.translation_service import do_translate
from services.voice_service import create_voice

translate_bp = Blueprint("translate", __name__)

# =========================
# CONFIG
# =========================
executor = ThreadPoolExecutor(max_workers=3)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

BASE_URL = "https://ouivocal-api.onrender.com"


# =========================
# TEXT TRANSLATION
# =========================
@translate_bp.route("/translate", methods=["POST"])
def translate_text():
    try:
        data = request.get_json()

        text = data.get("text")
        direction = data.get("direction")
        gender = data.get("gender", "female")

        if not text:
            return jsonify({"error": "No text provided"}), 400

        print("📝 Translating:", text)

        # 1️⃣ Translate FIRST
        translated = do_translate(text, direction)

        print("🌍 Translated:", translated)

        # 2️⃣ Generate audio
        audio_url = None

        try:
            filename = f"{uuid.uuid4().hex}.mp3"
            output_path = os.path.join(OUTPUT_FOLDER, filename)

            print("🔊 Generating voice...")

            create_voice(translated, direction, gender, output_path)

            # VERIFY FILE
            if os.path.exists(output_path):
                size = os.path.getsize(output_path)
                print("📏 Audio size:", size)

                if size > 1000:
                    audio_url = f"{BASE_URL}/audio/{filename}"
                else:
                    print("❌ Audio too small")
            else:
                print("❌ Audio not created")

        except Exception as e:
            print("VOICE ERROR:", e)

        return jsonify({
            "translated": translated,
            "audio": audio_url
        })

    except Exception as e:
        print("❌ TRANSLATE ERROR:", e)
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

        print("🎤 Audio received:", filepath)

        # 1️⃣ Transcribe
        text = transcribe_audio(filepath, direction)

        print("🧠 Transcribed:", text)

        if not text or "No speech" in text:
            return jsonify({
                "original": "",
                "translated": "⚠️ No speech detected",
                "audio": None
            })

        # 2️⃣ Translate
        translated = do_translate(text, direction)

        print("🌍 Translated:", translated)

        # 3️⃣ Generate voice
        audio_url = None

        try:
            out_filename = f"{uuid.uuid4().hex}.mp3"
            output_path = os.path.join(OUTPUT_FOLDER, out_filename)

            print("🔊 Generating voice...")

            create_voice(translated, direction, gender, output_path)

            if os.path.exists(output_path):
                size = os.path.getsize(output_path)
                print("📏 Audio size:", size)

                if size > 1000:
                    audio_url = f"{BASE_URL}/audio/{out_filename}"
                else:
                    print("❌ Audio too small")
            else:
                print("❌ Audio not created")

        except Exception as e:
            print("VOICE ERROR:", e)

        return jsonify({
            "original": text,
            "translated": translated,
            "audio": audio_url
        })

    except Exception as e:
        print("❌ AUDIO ERROR:", e)
        return jsonify({"error": "Audio failed"}), 500


# =========================
# LIVE MODE (FAST RESPONSE)
# =========================
@translate_bp.route("/audio-live", methods=["POST"])
def translate_audio_live():
    try:
        audio_file = request.files.get("audio")
        direction = request.form.get("direction")

        if not audio_file:
            return jsonify({"error": "No audio file"}), 400

        filename = f"{uuid.uuid4().hex}.webm"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        audio_file.save(filepath)

        # ⚡ FAST MODE (NO VOICE GENERATION)
        text = transcribe_audio(filepath, direction)

        if not text:
            return jsonify({
                "original": "",
                "translated": ""
            })

        translated = do_translate(text, direction)

        return jsonify({
            "original": text,
            "translated": translated
        })

    except Exception as e:
        print("❌ LIVE ERROR:", e)
        return jsonify({"error": "Live failed"}), 500