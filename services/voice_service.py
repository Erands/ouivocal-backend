import edge_tts
import asyncio
import os


# ✅ Voice selector (stable + clean)
def get_voice(direction, gender):
    gender = (gender or "female").lower()

    if direction == "en-fr":
        return "fr-FR-HenriNeural" if gender == "male" else "fr-FR-DeniseNeural"
    else:
        return "en-US-GuyNeural" if gender == "male" else "en-US-JennyNeural"


# ✅ SAFE AUDIO GENERATOR (SYNC — VERY IMPORTANT)
def create_voice(text, direction, gender, output_path):

    try:
        voice = get_voice(direction, gender)

        async def generate():
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)

        # 🔥 ALWAYS WAIT (this is the fix)
        asyncio.run(generate())

        # 🔍 VERIFY FILE
        if not os.path.exists(output_path):
            print("❌ File not created:", output_path)
            return None

        size = os.path.getsize(output_path)

        if size < 1000:
            print("❌ File too small (invalid audio):", size)
            return None

        print("✅ Audio created:", output_path, "| Size:", size)

        return output_path

    except Exception as e:
        print("❌ Voice error:", e)
        return None