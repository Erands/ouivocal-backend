from faster_whisper import WhisperModel

# =========================
# 🔥 OPTIMIZED MODEL LOAD
# =========================
# Use CPU-friendly settings for Render
model = WhisperModel(
    "tiny",
    device="cpu",
    compute_type="int8"   # 🔥 BIG speed boost on CPU
)

# =========================
# 🎤 FAST TRANSCRIBE
# =========================
def transcribe_audio(path, direction):
    try:
        # Detect source language
        source_lang = "fr" if direction == "fr-en" else "en"

        # 🔥 FAST SETTINGS
        segments, _ = model.transcribe(
            path,
            language=source_lang,
            beam_size=1,              # 🔥 faster than default (5)
            best_of=1,                # 🔥 reduce compute
            vad_filter=True,          # 🔥 skip silence (BIG speed boost)
            vad_parameters=dict(
                min_silence_duration_ms=500
            )
        )

        text = " ".join([s.text for s in segments]).strip()

        if not text:
            return "⚠️ No speech detected"

        return text

    except Exception as e:
        print("Whisper error:", e)
        return "⚠️ Audio processing failed"