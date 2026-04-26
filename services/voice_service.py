import edge_tts
import asyncio
import os
import uuid

# 🔥 Ensure output folder exists
OUTPUT_FOLDER = "outputs"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# ✅ Voice selector (stable)
def get_voice(direction, gender):
    if direction == "en-fr":
        return "fr-FR-HenriNeural" if gender == "male" else "fr-FR-DeniseNeural"
    else:
        return "en-US-GuyNeural" if gender == "male" else "en-US-JennyNeural"


# ✅ Proper async runner (fixes empty/invalid files)
def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return asyncio.create_task(coro)
    except RuntimeError:
        pass

    return asyncio.run(coro)


# ✅ MAIN FUNCTION (PRODUCTION SAFE)
def create_voice(text, direction, gender):

    try:
        # 🔥 Generate unique filename
        filename = f"{uuid.uuid4().hex}.wav"
        output_path = os.path.join(OUTPUT_FOLDER, filename)

        voice = get_voice(direction, gender)

        async def generate():
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)

        # 🔥 Run TTS
        run_async(generate())

        # 🔥 Validate file (VERY IMPORTANT)
        if not os.path.exists(output_path):
            print("❌ Audio not created")
            return None

        size = os.path.getsize(output_path)

        if size < 1000:
            print("❌ Audio too small / invalid:", size)
            return None

        print("✅ Audio created:", output_path, "Size:", size)

        # 🔥 RETURN ONLY FILENAME (NOT FULL PATH)
        return filename

    except Exception as e:
        print("❌ Voice error:", e)
        return None