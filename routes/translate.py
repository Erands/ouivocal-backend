from flask import Blueprint, request, jsonify
import os
import uuid
import traceback

from services.audio_service import transcribe_audio
from services.translation_service import do_translate
from services.voice_service import create_voice

translate_bp = Blueprint("translate", __name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# =========================
# TEXT TRANSLATION (BULLETPROOF)
# =========================
@translate_bp.route("/translate", methods=["POST"])
def translate_text():
    try:
        data = request.json or {}

        text = data.get("text") or ""
        direction = data.get("direction") or "en-fr"
        gender = data.get("gender") or "female"

        print("INPUT:", text, direction, gender)

        # ✅ ALWAYS RETURN SOMETHING
        if not text.strip():
            return jsonify({
                "translated": "⚠️ Empty input",
                "audio": None
            })

        # 🔥 SAFE TRANSLATION
        try:
            translated = do_translate(text, direction)
        except Exception as e:
            print("TRANSLATION ERROR:", e)
            translated = text  # fallback

        # 🔥 SAFE AUDIO
        audio_url = None
        try:
            filename = f"{uuid.uuid4().hex}.mp3"
            output_path = os.path.join(OUTPUT_FOLDER, filename)

            create_voice(translated, direction, gender, output_path)

            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                audio_url = f"https://ouivocal-api.onrender.com/audio/{filename}"

        except Exception as e:
            print("VOICE ERROR:", e)

        return jsonify({
            "translated": translated,
            "audio": audio_url
        })

    except Exception as e:
        print("🔥 CRITICAL ERROR:")
        traceback.print_exc()

        # ✅ NEVER CRASH FRONTEND AGAIN
        return jsonify({
            "translated": "⚠️ Server error (check logs)",
            "audio": None
        })


# =========================
# AUDIO TRANSLATION (SAFE)
# =========================
@translate_bp.route("/audio", methods=["POST"])
def translate_audio():
    try:
        audio_file = request.files.get("audio")
        direction = request.form.get("direction") or "en-fr"
        gender = request.form.get("gender") or "female"

        if not audio_file:
            return jsonify({
                "translated": "⚠️ No audio file",
                "audio": None
            })

        filename = f"{uuid.uuid4().hex}.webm"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        audio_file.save(filepath)

        # 🔥 SAFE TRANSCRIBE
        try:
            text = transcribe_audio(filepath, direction)
        except Exception as e:
            print("TRANSCRIBE ERROR:", e)
            text = ""

        if not text:
            return jsonify({
                "original": "",
                "translated": "⚠️ No speech detected",
                "audio": None
            })

        # 🔥 SAFE TRANSLATE
        try:
            translated = do_translate(text, direction)
        except Exception as e:
            print("TRANSLATE ERROR:", e)
            translated = text

        # 🔥 SAFE AUDIO
        audio_url = None
        try:
            audio_filename = f"{uuid.uuid4().hex}.mp3"
            output_path = os.path.join(OUTPUT_FOLDER, audio_filename)

            create_voice(translated, direction, gender, output_path)

            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                audio_url = f"https://ouivocal-api.onrender.com/audio/{audio_filename}"

        except Exception as e:
            print("VOICE ERROR:", e)

        return jsonify({
            "original": text,
            "translated": translated,
            "audio": audio_url
        })

    except Exception as e:
        print("🔥 AUDIO CRASH:")
        traceback.print_exc()

        return jsonify({
            "translated": "⚠️ Audio processing failed",
            "audio": None
        })


# =========================
# LIVE MODE (FAST + SAFE)
# =========================
@translate_bp.route("/audio-live", methods=["POST"])
def translate_audio_live():
    try:
        audio_file = request.files.get("audio")
        direction = request.form.get("direction") or "en-fr"

        if not audio_file:
            return jsonify({"translated": "", "audio": None})

        filename = f"{uuid.uuid4().hex}.webm"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        audio_file.save(filepath)

        try:
            text = transcribe_audio(filepath, direction)
        except:
            text = ""

        if not text:
            return jsonify({"translated": "", "audio": None})

        try:
            translated = do_translate(text, direction)
        except:
            translated = text

        return jsonify({
            "original": text,
            "translated": translated,
            "audio": None
        })

    except Exception as e:
        print("🔥 LIVE CRASH:")
        traceback.print_exc()
        return jsonify({"translated": "", "audio": None})