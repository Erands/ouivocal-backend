from faster_whisper import WhisperModel

# 🔥 Use lightweight model (important for your system)
model = WhisperModel("tiny")

def transcribe_audio(path, direction):
    try:
        source_lang = "fr" if direction == "fr-en" else "en"

        segments, _ = model.transcribe(path, language=source_lang)

        text = " ".join([s.text for s in segments]).strip()

        if not text:
            return "⚠️ No speech detected"

        return text

    except Exception as e:
        print("Whisper error:", e)
        return "⚠️ Audio processing failed"