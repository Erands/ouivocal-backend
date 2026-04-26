from faster_whisper import WhisperModel

# 🔥 FAST + LIGHT MODEL
model = WhisperModel(
    "tiny",
    compute_type="int8",
    cpu_threads=2
)

def transcribe_audio(path, direction):
    try:
        source_lang = "fr" if direction == "fr-en" else "en"

        segments, _ = model.transcribe(
            path,
            language=source_lang,
            beam_size=1  # 🔥 speed boost
        )

        text = " ".join([s.text for s in segments]).strip()

        if not text:
            return "⚠️ No speech detected"

        return text

    except Exception as e:
        print("Whisper error:", e)
        return "⚠️ Audio processing failed"