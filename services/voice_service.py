import edge_tts
import asyncio
import os
import uuid

OUTPUT_FOLDER = "outputs"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# ✅ Voice selector
def get_voice(direction, gender):
    if direction == "en-fr":
        return "fr-FR-HenriNeural" if gender == "male" else "fr-FR-DeniseNeural"
    else:
        return "en-US-GuyNeural" if gender == "male" else "en-US-JennyNeural"


# ✅ Async runner (FIXED — NO background tasks)
def run_async(coro):
    return asyncio.run(coro)


# ✅ MAIN FUNCTION (FINAL FIX)
def create_voice(text, direction, gender):

    try:
        filename = f"{uuid.uuid4().hex}.mp3"   # 🔥 MP3 (browser safe)
        output_path = os.path.join(OUTPUT_FOLDER, filename)

        voice = get_voice(direction, gender)

        async def generate():
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)

        # 🔥 MUST BLOCK until finished
        run_async(generate())

        # 🔥 VERIFY FILE
        if not os.path.exists(output_path):
            print("❌ Audio not created")
            return None

        size = os.path.getsize(output_path)

        if size < 1000:
            print("❌ Audio too small:", size)
            return None

        print("✅ Audio created:", filename, "Size:", size)

        return filename

    except Exception as e:
        print("❌ Voice error:", e)
        return None