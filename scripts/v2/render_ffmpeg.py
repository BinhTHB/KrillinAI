import subprocess
from pathlib import Path

from config import load_config
from logger import get_logger

logger = get_logger("RenderFFmpeg")


def _has_valid_subtitles(path: Path) -> bool:
    try:
        return path.exists() and "-->" in path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False


def _escape_filter_path(path: Path) -> str:
    return path.name.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def _probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def _has_audio_stream(path: Path) -> bool:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=index",
            "-of",
            "csv=p=0",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and bool(result.stdout.strip())


def build_render_command(
    video_path: Path,
    subtitle_path: Path,
    tts_audio_path: Path,
    output_path: Path,
    subtitle_height: int | None = None,
    use_subtitles: bool = True,
) -> list[str]:
    cfg = load_config()
    video_duration = _probe_duration(video_path)
    subtitle_height = subtitle_height or cfg.subtitle_height
    has_original_audio = _has_audio_stream(video_path)

    cmd = ["ffmpeg", "-y", "-i", video_path.name, "-i", tts_audio_path.name]
    filter_parts: list[str] = []

    if use_subtitles:
        subs = _escape_filter_path(subtitle_path)
        force_style = f"Alignment=2,MarginV={cfg.subtitle_margin_v}"
        filter_parts.append(
            f"[0:v]crop=iw:{subtitle_height}:0:ih-{subtitle_height},boxblur={cfg.blur_power}:{cfg.blur_radius}[blur]"
        )
        filter_parts.append(f"[0:v][blur]overlay=0:H-{subtitle_height}[blurred]")
        filter_parts.append(f"[blurred]subtitles=filename='{subs}':force_style='{force_style}'[v]")
        video_map = "[v]"
        video_codec = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23"]
    else:
        video_map = "0:v:0"
        video_codec = ["-c:v", "copy"]

    if has_original_audio:
        filter_parts.append(f"[0:a:0]volume={cfg.bg_volume}[bg]")
        filter_parts.append(f"[1:a:0]volume={cfg.voice_volume},apad,atrim=0:{video_duration:.3f}[tts]")
        filter_parts.append("[bg][tts]amix=inputs=2:duration=first:dropout_transition=0[a]")
    else:
        filter_parts.append(f"[1:a:0]volume={cfg.voice_volume},apad,atrim=0:{video_duration:.3f}[a]")

    if filter_parts:
        cmd.extend(["-filter_complex", ";".join(filter_parts)])

    cmd.extend(["-map", video_map, *video_codec])
    cmd.extend(["-map", "[a]", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", output_path.name])
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