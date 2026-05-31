from faster_whisper import WhisperModel

# 🚀 HIGHER ACCURACY CONFIG
model = WhisperModel(
    "small",
    compute_type="int8",
    cpu_threads=4
)


def transcribe_audio(path, direction):
    try:

        segments, info = model.transcribe(
            path,

            # Better recognition
            beam_size=8,

            # Better candidate search
            best_of=5,

            # Remove silence/noise
            vad_filter=True,

            # More accurate decoding
            temperature=0.0,

            # Better long-form speech
            condition_on_previous_text=True,

            # Word timestamps help segmentation
            word_timestamps=True
        )

        text_parts = []

        for segment in segments:
            cleaned = segment.text.strip()

            if cleaned:
                text_parts.append(cleaned)

        text = " ".join(text_parts).strip()

        print("===================================")
        print("Detected language:", info.language)
        print("Language probability:", info.language_probability)
        print("Transcribed text:", text)
        print("===================================")

        if not text:
            return "⚠️ No speech detected"

        return text

    except Exception as e:
        print("Whisper error:", e)
        return "⚠️ Audio processing failed"