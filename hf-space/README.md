---
title: KrillinAI ASR
emoji: 🎙️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

# KrillinAI ASR — Faster-Whisper Transcription Service

Lightweight CPU transcription service for KrillinAI v2 pipeline.

- **Model**: `base` (CPU / int8) — configurable via `WHISPER_MODEL`, `WHISPER_DEVICE`, `WHISPER_COMPUTE_TYPE`
- **Endpoints**: `GET /health`, `POST /transcribe`
- **Audio input**: multipart/form-data (FLAC / WAV / MP3)
- **Output**: SRT with word-level timestamps

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WHISPER_MODEL` | `base` | Faster-Whisper model name |
| `WHISPER_DEVICE` | `cpu` | Device (`cpu`, `cuda`) |
| `WHISPER_COMPUTE_TYPE` | `int8` | Compute type (`int8`, `float16`) |
| `PORT` | `7860` | FastAPI port |

GPU overrides (paid hardware): set `WHISPER_MODEL=distil-large-v3`, `WHISPER_DEVICE=cuda`, `WHISPER_COMPUTE_TYPE=float16`.
