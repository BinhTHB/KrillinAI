#!/usr/bin/env python3
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from render_ffmpeg import build_render_command


def test_build_render_command_blurs_subtitles_and_uses_tts_audio() -> None:
    command = build_render_command(
        Path("workdir/job/video_orig.mp4"),
        Path("workdir/job/translated_vi.srt"),
        Path("workdir/job/tts_voice.wav"),
        Path("workdir/job/video_final.mp4"),
    )
    joined = " ".join(command)

    assert command[0] == "ffmpeg"
    assert "crop=iw:120:0:ih-120" in joined
    assert "boxblur=10:5" in joined
    assert "subtitles=" in joined
    assert "-map 1:a:0" in joined
    assert "workdir\\job\\video_final.mp4" in joined or "workdir/job/video_final.mp4" in joined


if __name__ == "__main__":
    test_build_render_command_blurs_subtitles_and_uses_tts_audio()
    print("All render FFmpeg tests passed.")
