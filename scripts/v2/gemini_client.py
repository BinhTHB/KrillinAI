import os
import asyncio
import requests
import tempfile
import subprocess
from pathlib import Path
from config import load_config
from logger import get_logger

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

logger = get_logger("GeminiClient")


class GeminiClient:
    def __init__(self) -> None:
        self.cfg = load_config()

    def translate_srt(self, srt_text: str, target_language: str = "vi") -> str:
        if self.cfg.dry_run:
            logger.info(f"[DRY RUN] Translating SRT to {target_language}")
            return srt_text.replace("[Dry run]", "[Dry run translated]")

        if not self.cfg.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        model = self.cfg.gemini_model or "gemini-3.1-flash-lite"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        prompt = (
            "You are a professional subtitle translator. Translate the following subtitles to "
            f"{target_language}. Preserve all SRT indexes, timestamps, blank lines, and formatting exactly. "
            "Translate only subtitle text. Return only valid SRT.\n\n"
            f"{srt_text}"
        )
        response = requests.post(
            url,
            params={"key": self.cfg.gemini_api_key},
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError) as exc:
            logger.error(f"Failed to parse Gemini response: {data}")
            raise RuntimeError(f"Failed to parse Gemini response: {exc}")

    def synthesize_voice(self, text: str, voice: str = "") -> bytes:
        if self.cfg.dry_run:
            logger.info("[DRY RUN] Generating placeholder Gemini voice audio")
            return b"KRILLINAI_DRY_RUN_GEMINI_TTS"

        if not self.cfg.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not configured")
        if genai is None or types is None:
            raise RuntimeError("google-genai SDK is required for Gemini Live TTS")

        return asyncio.run(self._synthesize_voice_live(text, voice or "Puck"))

    async def _synthesize_voice_live(self, text: str, voice: str) -> bytes:
        model = os.getenv("GEMINI_TTS_MODEL", "gemini-3.1-flash-live-preview")
        client = genai.Client(api_key=self.cfg.gemini_api_key, http_options={"api_version": "v1alpha"})
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                ),
                language_code="vi-VN",
            ),
            system_instruction=(
                "You are a text-to-speech engine. Read the user's message aloud in Vietnamese. "
                "Do not add any words, explanations, or meta statements. Only output audio."
            ),
        )
        received_audio = bytearray()
        async with client.aio.live.connect(model=model, config=config) as session:
            await session.send_client_content(
                turns=[types.Content(role="user", parts=[types.Part(text=text)])],
                turn_complete=True,
            )
            async for msg in session.receive():
                if msg.data:
                    received_audio.extend(msg.data)
                if msg.server_content and msg.server_content.turn_complete:
                    break
        if not received_audio:
            raise RuntimeError("No audio bytes received from Gemini Live API")
        return self._pcm_to_wav(bytes(received_audio))

    def _pcm_to_wav(self, pcm_bytes: bytes) -> bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            out_wav = Path(tmp.name)
        temp_pcm = out_wav.with_suffix(".raw.pcm")
        try:
            temp_pcm.write_bytes(pcm_bytes)
            result = subprocess.run(
                f'ffmpeg -y -f s16le -ar 24000 -ac 1 -i "{temp_pcm}" -ac 1 -ar 44100 "{out_wav}"',
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.decode("utf-8", errors="ignore")[:500])
            return out_wav.read_bytes()
        finally:
            if temp_pcm.exists():
                temp_pcm.unlink()
            if out_wav.exists():
                out_wav.unlink()
