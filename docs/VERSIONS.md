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

- **Docker Base**: `python:3.10-slim` (lightweight CPU-only image for free-tier deployment).
- **Python**: `3.10`
- **FastAPI**: `^0.100.0`
- **Uvicorn**: `^0.22.0`
- **python-multipart**: `^0.0.6` (required for file uploads).
- **PyTorch**: `^2.0.0` (CPU and GPU compatible).
- **Faster-Whisper**: `^1.0.0`
- **ctranslate2**: (Bundled automatically by Faster-Whisper, matches model quantization).

## Workflow Python dependencies

- **boto3**: `latest` (AWS S3 Python SDK used to access Cloudflare R2 bucket).
- **requests**: `latest` (HTTP library for calling HF Space /transcribe and Gemini API).
- **google-api-python-client**: `latest` (Google Drive upload client).
- **google-auth-httplib2**: `latest` (Google API HTTP auth transport).
- **google-auth-oauthlib**: `latest` (Google auth helper dependency used by the Drive client stack).

---

## Upgrade Guidelines

1. **yt-dlp**: Should always be fetched fresh in the workflow run (using `pip install yt-dlp` without pinning) to avoid download failures due to YouTube backend changes.
2. **PyTorch**: For GPU deployments, ensure the PyTorch version matches the CUDA runtime. The CPU-only Free Tier does not require CUDA.
3. **Faster-Whisper**: Major version updates must be tested locally to verify compatibility with existing Whisper model file formats on Hugging Face.
