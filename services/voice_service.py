import edge_tts
import asyncio

async def generate_voice(text, voice, output_path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

def create_voice(text, direction, voiceType, output_path):
    if direction == "fr-en":
        voice = "en-US-GuyNeural" if voiceType == "male" else "en-US-JennyNeural"
    else:
        voice = "fr-FR-HenriNeural" if voiceType == "male" else "fr-FR-DeniseNeural"

    asyncio.run(generate_voice(text, voice, output_path))