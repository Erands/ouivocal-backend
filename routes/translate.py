from flask import Blueprint, request, jsonify
import os
import uuid

from services.audio_service import transcribe_audio
from services.translation_service import do_translate
from services.voice_service import create_voice

translate_bp = Blueprint("translate", __name__)

# =========================
# CONFIG
# =========================
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
            return jsonify({
                "translated": "⚠️ No text provided",
                "audio": None
            })

        print("📝 Input:", text)

        # 1️⃣ TRANSLATE
        translated = do_translate(text, direction)
        print("🌍 Translated:", translated)

        # 2️⃣ GENERATE AUDIO (🔥 FIXED)
        audio_url = None

        try:
            audio_filename = create_voice(translated, direction, gender)

            if audio_filename:
                audio_url = f"{BASE_URL}/audio/{audio_filename}"
                print("🔊 Audio URL:", audio_url)
            else:
                print("❌ Audio generation failed")

        except Exception as e:
            print("❌ Voice error:", e)

        return jsonify({
            "translated": translated,
            "audio": audio_url
        })

    except Exception as e:
        print("❌ TRANSLATE ERROR:", e)
        return jsonify({
            "translated": "⚠️ Server error",
            "audio": None
        })


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
            return jsonify({
                "translated": "⚠️ No audio file",
                "audio": None
            })

        filename = f"{uuid.uuid4().hex}.webm"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        audio_file.save(filepath)

        print("🎤 Audio received:", filepath)

        # 1️⃣ TRANSCRIBE
        text = transcribe_audio(filepath, direction)
        print("🧠 Transcribed:", text)

        if not text or "No speech" in text:
            return jsonify({
                "original": "",
                "translated": "⚠️ No speech detected",
                "audio": None
            })

        # 2️⃣ TRANSLATE
        translated = do_translate(text, direction)
        print("🌍 Translated:", translated)

        # 3️⃣ GENERATE AUDIO (🔥 FIXED)
        audio_url = None

        try:
            audio_filename = create_voice(translated, direction, gender)

            if audio_filename:
                audio_url = f"{BASE_URL}/audio/{audio_filename}"
                print("🔊 Audio URL:", audio_url)
            else:
                print("❌ Audio generation failed")

        except Exception as e:
            print("❌ Voice error:", e)

        return jsonify({
            "original": text,
            "translated": translated,
            "audio": audio_url
        })

    except Exception as e:
        print("❌ AUDIO ERROR:", e)
        return jsonify({
            "translated": "⚠️ Audio failed",
            "audio": None
        })


# =========================
# LIVE MODE (FAST - NO AUDIO)
# =========================
@translate_bp.route("/audio-live", methods=["POST"])
def translate_audio_live():
    try:
        audio_file = request.files.get("audio")
        direction = request.form.get("direction")

        if not audio_file:
            return jsonify({
                "translated": "",
                "audio": None
            })

        filename = f"{uuid.uuid4().hex}.webm"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        audio_file.save(filepath)

        # ⚡ FAST TRANSCRIBE
        text = transcribe_audio(filepath, direction)

        if not text:
            return jsonify({
                "translated": "",
                "audio": None
            })

        # ⚡ FAST TRANSLATE
        translated = do_translate(text, direction)

        return jsonify({
            "original": text,
            "translated": translated,
            "audio": None
        })

    except Exception as e:
        print("❌ LIVE ERROR:", e)
        return jsonify({
            "translated": "",
            "audio": None
        })