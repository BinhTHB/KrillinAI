import os
import requests
import base64
import wave
import tempfile
from pathlib import Path
from config import load_config
from logger import get_logger

logger = get_logger('GeminiClient')


class GeminiClient:
    def __init__(self) -> None:
        self.cfg = load_config()

    def translate_srt(self, srt_text: str, target_language: str = 'vi') -> str:
        if self.cfg.dry_run:
            logger.info(f'[DRY RUN] Translating SRT to {target_language}')
            return srt_text.replace('[Dry run]', '[Dry run translated]')

        if not self.cfg.gemini_api_key:
            raise ValueError('GEMINI_API_KEY is not configured')

        model = self.cfg.gemini_model or 'gemini-3.1-flash-lite'
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.cfg.gemini_api_key}'
        
        system_instruction = (
            'You are a professional subtitle translator. Translate the following subtitles into Vietnamese.\n'
            'CRITICAL: Keep the exact timecodes, indexes, and empty lines. Do NOT change line numbers.\n'
            'Only translate the actual subtitle text itself. Keep formatting tags like <i>, </i> if present.\n'
            'Ensure the translation is natural and accurate.'
        )
        
        headers = {'Content-Type': 'application/json'}
        data = {
            'contents': [
                {
                    'role': 'user',
                    'parts': [
                        {'text': f'{system_instruction}\n\nSubtitles to translate:\n{srt_text}'}
                    ]
                }
            ]
        }
        
        resp = requests.post(url, headers=headers, json=data, timeout=120)
        resp.raise_for_status()
        
        res_data = resp.json()
        try:
            translated = res_data['candidates'][0]['content']['parts'][0]['text']
            return translated.strip()
        except (KeyError, IndexError) as e:
            logger.error(f'Failed to parse Gemini response: {res_data}')
            raise RuntimeError(f'Failed to parse Gemini response: {e}')

    def synthesize_voice(self, text: str, voice: str = '') -> bytes:
        if self.cfg.dry_run:
            logger.info('[DRY RUN] Generating placeholder Gemini voice audio')
            return b'KRILLINAI_DRY_RUN_GEMINI_TTS'

        if not self.cfg.gemini_api_key:
            raise ValueError('GEMINI_API_KEY is not configured')

        tts_model = os.getenv('GEMINI_TTS_MODEL', 'gemini-3.1-flash-tts-preview')
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{tts_model}:generateContent?key={self.cfg.gemini_api_key}'
        selected_voice = voice or 'Kore'
        payload = {
            'contents': [{'parts': [{'text': text}]}],
            'generationConfig': {
                'responseModalities': ['AUDIO'],
                'speechConfig': {
                    'voiceConfig': {
                        'prebuiltVoiceConfig': {'voiceName': selected_voice}
                    }
                },
            },
        }
        response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        try:
            part = data['candidates'][0]['content']['parts'][0]
            inline_data = part.get('inlineData') or part.get('inline_data')
            audio_bytes = base64.b64decode(inline_data['data'])
            mime_type = inline_data.get('mimeType') or inline_data.get('mime_type', '')
            if 'wav' in mime_type.lower():
                return audio_bytes
            return self._pcm_to_wav(audio_bytes)
        except (KeyError, IndexError, TypeError) as exc:
            logger.error(f'Failed to parse Gemini TTS response: {data}')
            raise RuntimeError(f'Failed to parse Gemini TTS response: {exc}')

    def _pcm_to_wav(self, pcm_bytes: bytes) -> bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
            tmp_path = Path(tmp.name)
        try:
            with wave.open(str(tmp_path), 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(24000)
                wf.writeframes(pcm_bytes)
            return tmp_path.read_bytes()
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
