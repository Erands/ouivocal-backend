import edge_tts
import asyncio

# 🔥 FAST VOICE SELECTION
def get_voice(direction, gender):

    if direction == "en-fr":
        return "fr-FR-HenriNeural" if gender == "male" else "fr-FR-DeniseNeural"
    else:
        return "en-US-GuyNeural" if gender == "male" else "en-US-JennyNeural"


# 🔥 MAIN FUNCTION (UPDATED)
def create_voice(text, direction, gender, output_path):

    voice = get_voice(direction, gender)

    async def run():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)

    asyncio.run(run())

    return output_path