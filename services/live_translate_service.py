import speech_recognition as sr
from pydub import AudioSegment
from gtts import gTTS
import uuid
import os

from services.translation_service import do_translate

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def process_live_audio(file_path, direction):

    # convert to wav
    wav_file = file_path.replace(".webm", ".wav")

    sound = AudioSegment.from_file(file_path, format="webm")
    sound = sound + 20
    sound = sound.set_channels(1).set_frame_rate(16000)
    sound.export(wav_file, format="wav")

    # speech recognition
    r = sr.Recognizer()

    with sr.AudioFile(wav_file) as source:
        r.adjust_for_ambient_noise(source, duration=0.3)
        audio = r.record(source)

    try:
        text = r.recognize_google(audio)
    except:
        text = ""

    if not text:
        return None

    # translate
    translated = do_translate(text, direction)

    # text to speech
    output_file = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.mp3")

    tts = gTTS(text=translated, lang="en" if direction == "fr-en" else "fr")
    tts.save(output_file)

    # cleanup
    try:
        os.remove(file_path)
        os.remove(wav_file)
    except:
        pass

    return output_file