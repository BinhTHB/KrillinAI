import subprocess
from pathlib import Path

from logger import get_logger

logger = get_logger("RenderFFmpeg")


def _has_valid_subtitles(path: Path) -> bool:
    try:
        return path.exists() and "-->" in path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False


def _escape_subtitle_path(path: Path) -> str:
    return path.name.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def build_render_command(
    video_path: Path,
    subtitle_path: Path,
    tts_audio_path: Path,
    output_path: Path,
    subtitle_height: int = 120,
    use_subtitles: bool = True,
) -> list[str]:
    cmd = ["ffmpeg", "-y", "-i", video_path.name, "-i", tts_audio_path.name]
    if use_subtitles:
        subs = _escape_subtitle_path(subtitle_path)
        flt = (
            f"[0:v]crop=iw:{subtitle_height}:0:ih-{subtitle_height},boxblur=10:5[blur];"
            f"[0:v][blur]overlay=0:H-{subtitle_height},subtitles=filename='{subs}'[v]"
        )
        cmd.extend(["-filter_complex", flt, "-map", "[v]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23"])
    else:
        cmd.extend(["-map", "0:v:0", "-c:v", "copy"])
    cmd.extend(["-map", "1:a:0", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", output_path.name])
    return cmd


def render_video(
    video_path: Path,
    subtitle_path: Path,
    tts_audio_path: Path,
    output_path: Path,
) -> None:
    for p in (video_path, subtitle_path, tts_audio_path):
        if not p.exists():
            raise FileNotFoundError(f"Required render input missing: {p}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    use_subs = _has_valid_subtitles(subtitle_path)
    cmd = build_render_command(video_path, subtitle_path, tts_audio_path, output_path, use_subtitles=use_subs)
    logger.info("Running FFmpeg render %s", "with subtitles" if use_subs else "without subtitles (SRT empty/invalid)")
    subprocess.run(cmd, check=True, cwd=video_path.parent)
