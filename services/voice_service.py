import edge_tts
import asyncio
import os

# ✅ Voice selector
def get_voice(direction, gender):
    if direction == "en-fr":
        return "fr-FR-HenriNeural" if gender == "male" else "fr-FR-DeniseNeural"
    else:
        return "en-US-GuyNeural" if gender == "male" else "en-US-JennyNeural"


# ✅ SAFE ASYNC RUNNER (FIXES EMPTY AUDIO)
def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        return asyncio.create_task(coro)
    else:
        return asyncio.run(coro)


# ✅ MAIN FUNCTION (FIXED)
def create_voice(text, direction, gender, output_path):

    voice = get_voice(direction, gender)

    async def generate():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)

    # 🔥 RUN PROPERLY
    run_async(generate())

    # 🔥 VERIFY FILE (VERY IMPORTANT)
    if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
        print("❌ Audio file invalid or empty:", output_path)
        return None

    print("✅ Audio created:", output_path)

    return output_path