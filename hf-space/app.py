# Hugging Face Space – Faster-Whisper Transcription Service
# -------------------------------------------------------
# Exposes /health and /transcribe endpoints.
# Uses faster-whisper (distil-large-v3 by default, configurable via WHISPER_MODEL).
# Accepts multipart/form-data audio file, returns SRT with word-level timestamps.
# -------------------------------------------------------

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import PlainTextResponse
from faster_whisper import WhisperModel
import os
import tempfile
import time

app = FastAPI(title="KrillinAI Whisper Transcription")

# Model loaded at startup (blocking). Use /health to check readiness.
MODEL_NAME = os.getenv("WHISPER_MODEL", "distil-large-v3")
DEVICE = os.getenv("WHISPER_DEVICE", "auto")  # "auto", "cpu", "cuda"
COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "float16")

model = None
model_loading = False
model_ready = False


def load_model():
    global model, model_loading, model_ready
    if model is not None:
        return
    if model_loading:
        return
    model_loading = True
    try:
        model = WhisperModel(MODEL_NAME, device=DEVICE, compute_type=COMPUTE_TYPE)
        model_ready = True
    except Exception as e:
        model_ready = False
        print(f"Model load failed: {e}")
    finally:
        model_loading = False


@app.on_event("startup")
async def startup():
    load_model()


@app.get("/health")
async def health():
    """Return model loading status. Used by GitHub Action to wait until ready."""
    return {
        "status": "ready" if model_ready else ("loading" if model_loading else "not_started"),
        "model": MODEL_NAME,
    }


def format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format: HH:MM:SS,mmm"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"


def srt_from_segments(segments) -> str:
    """Build SRT with word-level timestamps (one line per word)."""
    lines = []
    idx = 1
    for seg in segments:
        if seg.words:
            for w in seg.words:
                lines.append(str(idx))
                lines.append(f"{format_timestamp(w.start)} --> {format_timestamp(w.end)}")
                lines.append(w.word.strip())
                lines.append("")
                idx += 1
        else:
            # fallback: whole segment as one block
            lines.append(str(idx))
            lines.append(f"{format_timestamp(seg.start)} --> {format_timestamp(seg.end)}")
            lines.append(seg.text.strip())
            lines.append("")
            idx += 1
    return "\n".join(lines)


@app.post("/transcribe", response_class=PlainTextResponse)
async def transcribe(
    file: UploadFile = File(..., description="Audio file (FLAC/WAV/MP3)"),
    language: str = Form(None, description="ISO language code (e.g. zh, en, vi). Auto if empty."),
    vad_filter: bool = Form(True, description="Enable VAD filter for speech segments"),
    word_timestamps: bool = Form(True, description="Return per-word timestamps"),
):
    if not model_ready:
        raise HTTPException(status_code=503, detail="Model not ready yet")

    # Save uploaded file to temp location
    suffix = os.path.splitext(file.filename)[1] or ".flac"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        segments, _ = model.transcribe(
            tmp_path,
            language=language,
            vad_filter=vad_filter,
            word_timestamps=word_timestamps,
        )
        # Convert generator to list
        segments_list = list(segments)
        return srt_from_segments(segments_list)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "7860")))
