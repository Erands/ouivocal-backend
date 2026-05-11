from faster_whisper import WhisperModel

# ✅ BETTER MODEL FOR ACCURATE TRANSCRIPTION
# small = good balance of speed + accuracy
model = WhisperModel(
    "small",
    compute_type="int8",
    cpu_threads=4
)


def transcribe_audio(path, direction):
    try:

        # ✅ AUTO-DETECT LANGUAGE
        # ✅ REMOVE SILENCE/NOISE
        # ✅ BETTER ACCURACY
        segments, info = model.transcribe(
            path,
            beam_size=5,
            vad_filter=True
        )

        # ✅ COMBINE TRANSCRIBED SEGMENTS
        text = " ".join([segment.text for segment in segments]).strip()

        # ✅ DEBUG LOG
        print("Detected language:", info.language)
        print("Transcribed text:", text)

        # ✅ EMPTY CHECK
        if not text:
            return "⚠️ No speech detected"

        return text

    except Exception as e:
        print("Whisper error:", e)
        return "⚠️ Audio processing failed"