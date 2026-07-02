#!/usr/bin/env python
"""Blur original hardcoded subtitles using boxblur on subtitle region.

Usage:
  python scripts/render_with_sub_blur.py \\
    --input-video origin_video.mp4 \\
    --origin-srt origin_language_srt.srt \\
    --overlay-srt controlled_gemini_live_resume/controlled_aligned.srt \\
    --output-video final_dubbed_blurred.mp4

The script:
1. Extracts timestamps from origin SRT
2. Builds FFmpeg filter_complex that:
   - Crops subtitle region
   - Applies boxblur to cropped region
   - Overlays blurred region back onto base video only during subtitle timestamps
   - Overlays Vietnamese ASS subtitles on top
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def parse_srt_cues(srt_path: str) -> list[tuple[float, float]]:
    """Extract (start_seconds, end_seconds) pairs from an SRT file."""
    cues: list[tuple[float, float]] = []
    text = Path(srt_path).read_text(encoding="utf-8").strip()
    for block in text.split("\n\n"):
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        timestamp_line = lines[1]
        parts = timestamp_line.split(" --> ")
        if len(parts) != 2:
            continue

        def to_seconds(ts: str) -> float:
            ts = ts.strip().replace(",", ".")
            h, m, s = ts.split(":")
            return float(h) * 3600 + float(m) * 60 + float(s)

        cues.append((to_seconds(parts[0]), to_seconds(parts[1])))
    return cues


def get_video_resolution(video_path: str) -> tuple[int, int]:
    """Return (width, height) of the video."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    w_str, h_str = result.stdout.strip().split(",")
    return int(w_str), int(h_str)


def escape_filter_path(path: str) -> str:
    """Escape a Windows path for use inside an FFmpeg filter argument.

    FFmpeg on Windows needs ``\\\\:`` (two backslashes) to escape the
    drive letter colon, otherwise the colon is interpreted as a filter
    option separator and the path is mis-parsed as an image size.
    """
    p = str(Path(path).resolve())
    p = p.replace("\\", "/")
    p = p.replace(":", "\\\\:")
    return p


def build_enable_expr(cues: list[tuple[float, float]]) -> str:
    """Build FFmpeg 'enable' expression covering all cues."""
    terms = [f"between(t,{s:.3f},{e:.3f})" for s, e in cues]
    return "+".join(terms)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Blur original subs (boxblur) and overlay translated SRT"
    )
    parser.add_argument("--input-video", required=True)
    parser.add_argument("--origin-srt", required=True)
    parser.add_argument("--overlay-srt", required=True,
                        help="Overlay subtitle file (.srt or .ass)")
    parser.add_argument("--output-video", required=True)
    parser.add_argument("--crop-top", type=float, default=0.80,
                        help="Top edge of subtitle region (fraction of height)")
    parser.add_argument("--crop-bottom", type=float, default=0.95,
                        help="Bottom edge of subtitle region (fraction of height)")
    parser.add_argument("--crop-left", type=float, default=0.0,
                        help="Left edge of subtitle region (fraction of width)")
    parser.add_argument("--crop-right", type=float, default=1.0,
                        help="Right edge of subtitle region (fraction of width)")
    parser.add_argument("--blur-power", type=int, default=15,
                        help="Boxblur luma radius (higher = more blur)")
    parser.add_argument("--timed", action="store_true",
                        help="Only apply blur during subtitle cues instead of continuously")
    args = parser.parse_args()

    W, H = get_video_resolution(args.input_video)
    y1 = int(H * args.crop_top)
    y2 = int(H * args.crop_bottom)
    x1 = int(W * args.crop_left)
    x2 = int(W * args.crop_right)
    crop_w = x2 - x1
    crop_h = y2 - y1

    cues = parse_srt_cues(args.origin_srt)
    if not cues:
        print("No cues found in origin SRT", file=sys.stderr)
        return 1

    print(f"Video: {W}x{H}, subtitle region: x={x1} y={y1} w={crop_w} h={crop_h}")
    print(f"Cues: {len(cues)}")

    # Find ASS file
    overlaysrt = Path(args.overlay_srt)
    if not overlaysrt.exists():
        print(f"Overlay subtitle not found: {args.overlay_srt}", file=sys.stderr)
        return 1

    ass_path = overlaysrt
    if overlaysrt.suffix.lower() == ".srt":
        ass_path = overlaysrt.with_suffix(".ass")
        if not ass_path.exists():
            workdir = overlaysrt.parent
            common_ass = workdir / "formatted_horizontal_dubbed.ass"
            if common_ass.exists():
                ass_path = common_ass
            else:
                print(f"Converting SRT to ASS: {ass_path}", file=sys.stderr)
                convert_cmd = [
                    "ffmpeg", "-y",
                    "-i", str(overlaysrt.resolve()),
                    str(ass_path.resolve()),
                ]
                result = subprocess.run(convert_cmd, capture_output=True)
                if result.returncode != 0:
                    print(f"Failed to convert SRT to ASS: {result.stderr.decode()}", file=sys.stderr)
                    return 1

    ass_escaped = escape_filter_path(str(ass_path.resolve()))
    enable_expr = build_enable_expr(cues)

    # Build filter_complex:
    # 1. Split input into [base] and [tocrop]
    # 2. Crop subtitle region from [tocrop] -> [cropped]
    # 3. Apply boxblur to [cropped] -> [blurred]
    # 4. Overlay [blurred] onto [base] at (x1,y1) only during subtitle timestamps -> [blurred_video]
    # 5. Apply ASS overlay on [blurred_video] -> final output
    #
    # The overlay filter supports 'enable' option for timeline editing.
    
    if args.timed:
        overlay_filter = f"overlay={x1}:{y1}:enable='{enable_expr}'"
    else:
        overlay_filter = f"overlay={x1}:{y1}"

    filter_complex = (
        f"[0:v]split=2[base][tocrop];"
        f"[tocrop]crop={crop_w}:{crop_h}:{x1}:{y1}[cropped];"
        f"[cropped]boxblur={args.blur_power}:1[blurred];"
        f"[base][blurred]{overlay_filter}[blurred_video];"
        f"[blurred_video]ass={ass_escaped}[outv]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(Path(args.input_video).resolve()),
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "0:a?",
        "-c:a", "copy",
        str(Path(args.output_video).resolve()),
    ]

    print(f"Running FFmpeg with {len(cues)} cues, blur_power={args.blur_power}...")
    preview = " ".join(str(c) for c in cmd[:5]) + f" ... (-filter_complex length={len(filter_complex)} chars)"
    print(preview)

    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        return result.returncode

    print(f"\nDone: {args.output_video}")
    return 0


if __name__ == "__main__":
    sys.exit(main())