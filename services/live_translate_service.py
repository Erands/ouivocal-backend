from faster_whisper import WhisperModel
from pydub import AudioSegment
import os

from services.translation_service import do_translate

# Load ONCE when server starts
model = WhisperModel(
    "medium",
    compute_type="int8",
    cpu_threads=2
)

def process_live_audio(file_path, direction):

    wav_file = file_path.replace(".webm", ".wav")

    try:

        # Convert to wav
        sound = AudioSegment.from_file(file_path, format="webm")
        sound = sound.set_channels(1)
        sound = sound.set_frame_rate(16000)
        sound.export(wav_file, format="wav")

        source_lang = "fr" if direction == "fr-en" else "en"

        segments, _ = model.transcribe(
            wav_file,
            language=source_lang,
            beam_size=1
        )

        text = " ".join(
            segment.text for segment in segments
        ).strip()

        if not text:
            return {
                "original": "",
                "translated": ""
            }

        translated = do_translate(
            text,
            direction
        )

        return {
            "original": text,
            "translated": translated
        }

    except Exception as e:

        print("LIVE ERROR:", e)

        return {
            "original": "",
            "translated": ""
        }

    finally:

        try:
            if os.path.exists(file_path):
                os.remove(file_path)

            if os.path.exists(wav_file):
                os.remove(wav_file)

        except:
            pass