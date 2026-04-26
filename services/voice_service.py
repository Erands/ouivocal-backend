import edge_tts
import uuid
import asyncio
import os

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# 🔊 ASYNC VOICE GENERATION
async def generate_voice(text, voice, filename):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(filename)


def create_voice(text, direction, gender):
    try:
        filename = f"{UPLOAD_FOLDER}/{uuid.uuid4().hex}.mp3"

        # 🎯 FIXED VOICE SELECTION
        if gender == "female":
            voice = "en-US-JennyNeural" if "en" in direction else "fr-FR-DeniseNeural"
        else:
            voice = "en-US-GuyNeural" if "en" in direction else "fr-FR-HenriNeural"

        asyncio.run(generate_voice(text, voice, filename))

        # 🔗 RETURN PUBLIC URL
        return f"https://ouivocal-api.onrender.com/{filename}"

    except Exception as e:
        print("Voice error:", e)
        return None