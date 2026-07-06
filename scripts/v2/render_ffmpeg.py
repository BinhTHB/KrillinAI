import subprocess
from pathlib import Path

from logger import get_logger

logger = get_logger("RenderFFmpeg")


def _escape_subtitle_path(path: Path) -> str:
    return str(path).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def build_render_command(
    video_path: Path,
    subtitle_path: Path,
    tts_audio_path: Path,
    output_path: Path,
    subtitle_height: int = 120,
) -> list[str]:
    subtitles = _escape_subtitle_path(subtitle_path)
    filter_complex = (
        f"[0:v]crop=iw:{subtitle_height}:0:ih-{subtitle_height},boxblur=10:5[blur];"
        f"[0:v][blur]overlay=0:H-{subtitle_height},subtitles=filename='{subtitles}'[v]"
    )
    return [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(tts_audio_path),
        "-filter_complex",
        filter_complex,
        "-map",
        "[v]",
        "-map",
        "1:a:0",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(output_path),
    ]


def render_video(
    video_path: Path,
    subtitle_path: Path,
    tts_audio_path: Path,
    output_path: Path,
) -> None:
    for path in (video_path, subtitle_path, tts_audio_path):
        if not path.exists():
            raise FileNotFoundError(f"Required render input missing: {path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = build_render_command(video_path, subtitle_path, tts_audio_path, output_path)
    logger.info("Running FFmpeg render")
    subprocess.run(command, check=True)
