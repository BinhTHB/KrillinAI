class StorageLayout:
    @staticmethod
    def get_job_prefix(job_id: str) -> str:
        return f"jobs/{job_id}"

    @staticmethod
    def get_video_orig_key(job_id: str) -> str:
        return f"jobs/{job_id}/video_orig.mp4"

    @staticmethod
    def get_audio_orig_key(job_id: str) -> str:
        return f"jobs/{job_id}/audio_orig.flac"

    @staticmethod
    def get_metadata_key(job_id: str) -> str:
        return f"jobs/{job_id}/metadata.json"

    @staticmethod
    def get_raw_srt_key(job_id: str) -> str:
        return f"jobs/{job_id}/raw_whisper.srt"

    @staticmethod
    def get_aligned_srt_key(job_id: str) -> str:
        return f"jobs/{job_id}/aligned.srt"

    @staticmethod
    def get_translated_srt_key(job_id: str) -> str:
        return f"jobs/{job_id}/translated_vi.srt"

    @staticmethod
    def get_tts_audio_key(job_id: str) -> str:
        return f"jobs/{job_id}/tts_voice.wav"

    @staticmethod
    def get_video_final_key(job_id: str) -> str:
        return f"jobs/{job_id}/video_final.mp4"
