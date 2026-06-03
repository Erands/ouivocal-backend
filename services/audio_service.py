from faster_whisper import WhisperModel
import time

# Fast startup + low memory
model = WhisperModel(
    "medium",
    compute_type="int8",
    cpu_threads=2
)

def transcribe_audio(path, direction):
    try:

        source_lang = "fr" if direction == "fr-en" else "en"

        start = time.time()

        segments, info = model.transcribe(
            path,
            language=source_lang,
            beam_size=1,
            vad_filter=True  # Ignore silence/background noise
        )

        text = " ".join(
            segment.text.strip()
            for segment in segments
        ).strip()

        elapsed = round(time.time() - start, 2)

        print(f"⏱ TRANSCRIBE: {elapsed}s")
        print(f"🌍 Detected language: {info.language}")
        print(f"📝 Transcribed text: {text}")

        # Ignore empty / garbage results
        if not text:
            return ""

        if len(text) < 3:
            return ""

        # Ignore common hallucinations
        garbage = [
            ".",
            ",",
            "...",
            "uh",
            "um"
        ]

        if text.lower() in garbage:
            return ""

        return text

    except Exception as e:
        print("❌ Whisper error:", e)
        return ""