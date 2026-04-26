from faster_whisper import WhisperModel

model = WhisperModel("base")

def transcribe_audio(path, direction):
    source_lang = "fr" if direction == "fr-en" else "en"
    segments, _ = model.transcribe(path, language=source_lang)
    return " ".join([s.text for s in segments]).strip()