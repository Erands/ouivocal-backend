from faster_whisper import WhisperModel

model = WhisperModel(
    "small",
    compute_type="int8",
    cpu_threads=4
)

def transcribe_audio(path, direction):
    try:

        segments, info = model.transcribe(
            path,
            beam_size=5,
            vad_filter=True
        )

        text = " ".join(
            segment.text.strip()
            for segment in segments
            if segment.text.strip()
        ).strip()

        print("Detected language:", info.language)
        print("Transcribed text:", text)

        if not text:
            return "⚠️ No speech detected"

        return text

    except Exception as e:
        print("Whisper error:", e)
        return "⚠️ Audio processing failed"