# KrillinAI v2 Version Matrix

Version reference matrix for all components in the KrillinAI v2 serverless pipeline.

## System & Runner

- **Runner Environment**: `Ubuntu 22.04 LTS` (via GitHub Actions `ubuntu-latest`).
- **Python**: `3.10.x` (standard across workflow scripts for dependency compatibility).
- **Node.js**: `22.x` (LTS, for Cloudflare Worker development and Wrangler CLI).

## Infrastructure tools

- **Wrangler**: `^3.0.0` (for Cloudflare Workers local emulation and deployment).
- **yt-dlp**: `latest` (essential for compatibility with breaking YouTube API updates).
- **FFmpeg**: `7.x` (system snap/apt package).
- **Docker**: `latest` (on runner for release job, and on HF Space runtime).

## Hugging Face Space (ASR Container)

- **Docker Base**: `nvidia/cuda:12.1.0-runtime-ubuntu22.04` (provides CUDA 12 support for GPU transcribing).
- **Python**: `3.10`
- **FastAPI**: `^0.100.0`
- **Uvicorn**: `^0.22.0`
- **python-multipart**: `^0.0.6` (required for file uploads).
- **PyTorch**: `^2.0.0` (compatible with CUDA 12.1 runtime).
- **Faster-Whisper**: `^1.0.0`
- **ctranslate2**: (Bundled automatically by Faster-Whisper, matches model quantization).

## Workflow Python dependencies

- **boto3**: `latest` (AWS S3 Python SDK used to access Cloudflare R2 bucket).
- **requests**: `latest` (HTTP library for calling HF Space /transcribe and Gemini API).

---

## Upgrade Guidelines

1. **yt-dlp**: Should always be fetched fresh in the workflow run (using `pip install yt-dlp` without pinning) to avoid download failures due to YouTube backend changes.
2. **PyTorch & CUDA**: If upgrading the Docker base to a newer CUDA version, verify that the PyTorch version matches the CUDA runtime to prevent whisper device loading errors.
3. **Faster-Whisper**: Major version updates must be tested locally to verify compatibility with existing Whisper model file formats on Hugging Face.
