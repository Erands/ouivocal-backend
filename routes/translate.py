from flask import Blueprint, request, jsonify
import os
import uuid
import traceback

from services.audio_service import transcribe_audio
from services.translation_service import do_translate
from services.voice_service import create_voice

translate_bp = Blueprint("translate", __name__)

# ✅ FOLDERS
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

        # ✅ TRANSLATE
        translated = do_translate(text, direction)

        # ✅ GENERATE AUDIO
        audio_filename = f"{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(OUTPUT_FOLDER, audio_filename)

        create_voice(translated, direction, gender, output_path)

        # ✅ VERIFY AUDIO EXISTS
        if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
            print("❌ Audio not generated properly")
            audio_url = None
        else:
            audio_url = f"https://ouivocal-api.onrender.com/audio/{audio_filename}"

        return jsonify({
            "translated": translated,
            "audio": audio_url
        })

    except Exception as e:
        print("❌ TEXT ERROR:")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


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

        # ✅ SAVE AUDIO INPUT
        filename = f"{uuid.uuid4().hex}.webm"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        audio_file.save(filepath)

        # ✅ TRANSCRIBE
        text = transcribe_audio(filepath, direction)

        if not text or text.strip() == "":
            return jsonify({
                "original": "",
                "translated": "⚠️ No speech detected",
                "audio": None
            })

        # ✅ TRANSLATE
        translated = do_translate(text, direction)

        # ✅ GENERATE AUDIO
        audio_filename = f"{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(OUTPUT_FOLDER, audio_filename)

        create_voice(translated, direction, gender, output_path)

        # ✅ VERIFY AUDIO
        if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
            print("❌ Audio failed")
            audio_url = None
        else:
            audio_url = f"https://ouivocal-api.onrender.com/audio/{audio_filename}"

        return jsonify({
            "original": text,
            "translated": translated,
            "audio": audio_url
        })

    except Exception as e:
        print("❌ AUDIO ERROR:")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# =========================
# LIVE MODE (REAL-TIME)
# =========================
@translate_bp.route("/audio-live", methods=["POST"])
def translate_audio_live():
    try:
        audio_file = request.files.get("audio")
        direction = request.form.get("direction")
        gender = request.form.get("gender", "female")

        if not audio_file:
            return jsonify({"error": "No audio file"}), 400

        # ✅ SAVE SMALL CHUNK
        filename = f"{uuid.uuid4().hex}.webm"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        audio_file.save(filepath)

        # ✅ QUICK TRANSCRIBE
        text = transcribe_audio(filepath, direction)

        if not text:
            return jsonify({
                "original": "",
                "translated": "",
                "audio": None
            })

        # ✅ QUICK TRANSLATE
        translated = do_translate(text, direction)

        # 🚫 NO AUDIO IN LIVE MODE (for speed)
        return jsonify({
            "original": text,
            "translated": translated,
            "audio": None
        })

    except Exception as e:
        print("❌ LIVE ERROR:")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500