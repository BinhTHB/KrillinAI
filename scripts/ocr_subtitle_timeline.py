#!/usr/bin/env python
"""Extract hard-sub subtitle timing from video frames using EasyOCR.

This script samples the lower part of a video, OCRs Chinese subtitle text, groups
stable text runs into SRT cues, and writes an OCR-derived origin subtitle file.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import cv2
import easyocr


CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
PUNCT_RE = re.compile(r"[\s，。！？、；：,.!?;:'\"“”‘’（）()\[\]【】《》<>…—_-]+")


@dataclass
class Sample:
    t: float
    text: str
    confidence: float


@dataclass
class Cue:
    start: float
    end: float
    text: str
    confidence: float


def normalize_text(text: str) -> str:
    text = text.strip()
    text = text.replace(" ", "")
    text = PUNCT_RE.sub("", text)
    return text


def has_cjk(text: str) -> bool:
    return bool(CJK_RE.search(text))


def similar_text(a: str, b: str) -> bool:
    na = normalize_text(a)
    nb = normalize_text(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    shorter, longer = (na, nb) if len(na) <= len(nb) else (nb, na)
    if len(shorter) >= 4 and shorter in longer:
        return True
    common = sum(1 for ch in shorter if ch in longer)
    return len(shorter) >= 4 and common / max(1, len(shorter)) >= 0.85


def merge_duplicate_cues(cues: list[Cue], max_gap: float = 1.0) -> list[Cue]:
    if not cues:
        return []
    merged: list[Cue] = []
    current = cues[0]
    for next_cue in cues[1:]:
        # Merge if duplicate or extremely similar text AND close enough (<= max_gap)
        if similar_text(current.text, next_cue.text) and (next_cue.start - current.end) <= max_gap:
            # Keep the longer text
            if len(normalize_text(next_cue.text)) > len(normalize_text(current.text)):
                current.text = next_cue.text
            current.end = next_cue.end
            current.confidence = (current.confidence + next_cue.confidence) / 2.0
        else:
            merged.append(current)
            current = next_cue
    merged.append(current)
    return merged


def fmt_ts(seconds: float) -> str:
    seconds = max(0.0, seconds)
    ms = int(round(seconds * 1000))
    h = ms // 3_600_000
    ms %= 3_600_000
    m = ms // 60_000
    ms %= 60_000
    s = ms // 1000
    ms %= 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def preprocess_crop(crop):
    crop = cv2.resize(crop, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 5, 50, 50)
    # Keep high contrast subtitle strokes while preserving colored outlines.
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def pick_text(result: Iterable, min_conf: float) -> tuple[str, float]:
    items = []
    for box, text, conf in result:
        if conf < min_conf:
            continue
        clean = text.strip()
        if not clean or not has_cjk(clean):
            continue
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        items.append((min(ys), min(xs), clean, float(conf)))
    if not items:
        return "", 0.0
    items.sort(key=lambda item: (round(item[0] / 20), item[1]))
    text = "".join(item[2] for item in items)
    conf = sum(item[3] for item in items) / len(items)
    return text, conf


def extract_samples(args) -> list[Sample]:
    video = Path(args.video)
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {video}")

    native_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = frame_count / native_fps if frame_count else 0.0
    step = 1.0 / args.sample_fps

    reader = easyocr.Reader(['ch_sim', 'en'], gpu=args.gpu, verbose=False)
    samples: list[Sample] = []
    t = args.start
    end = args.end if args.end > 0 else duration

    while t <= end + 1e-6:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ok, frame = cap.read()
        if not ok:
            break
        h, w = frame.shape[:2]
        y1 = max(0, min(h - 1, int(h * args.crop_top)))
        y2 = max(y1 + 1, min(h, int(h * args.crop_bottom)))
        x1 = max(0, min(w - 1, int(w * args.crop_left)))
        x2 = max(x1 + 1, min(w, int(w * args.crop_right)))
        crop = preprocess_crop(frame[y1:y2, x1:x2])
        result = reader.readtext(crop, detail=1, paragraph=False, decoder='greedy')
        text, conf = pick_text(result, args.min_conf)
        samples.append(Sample(t=t, text=text, confidence=conf))
        if args.verbose:
            print(f"{t:8.3f}s conf={conf:.2f} text={text}", flush=True)
        t += step

    cap.release()
    return samples


def group_samples(samples: list[Sample], max_gap: float, min_duration: float) -> list[Cue]:
    cues: list[Cue] = []
    active_text = ""
    active_start = 0.0
    active_end = 0.0
    confs: list[float] = []

    def close_active():
        nonlocal active_text, active_start, active_end, confs
        if active_text and active_end - active_start >= min_duration:
            cues.append(Cue(
                start=active_start,
                end=active_end,
                text=active_text,
                confidence=sum(confs) / max(1, len(confs)),
            ))
        active_text = ""
        active_start = active_end = 0.0
        confs = []

    for sample in samples:
        if not sample.text:
            if active_text and sample.t - active_end > max_gap:
                close_active()
            continue
        if not active_text:
            active_text = sample.text
            active_start = sample.t
            active_end = sample.t
            confs = [sample.confidence]
            continue
        if similar_text(active_text, sample.text) and sample.t - active_end <= max_gap:
            if len(normalize_text(sample.text)) > len(normalize_text(active_text)):
                active_text = sample.text
            active_end = sample.t
            confs.append(sample.confidence)
        else:
            close_active()
            active_text = sample.text
            active_start = sample.t
            active_end = sample.t
            confs = [sample.confidence]

    close_active()
    return cues


def write_srt(cues: list[Cue], path: Path):
    lines = []
    for i, cue in enumerate(cues, 1):
        lines.extend([
            str(i),
            f"{fmt_ts(cue.start)} --> {fmt_ts(cue.end)}",
            cue.text,
            "",
        ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="OCR hard-sub subtitle timeline from video")
    parser.add_argument("--video", required=True)
    parser.add_argument("--output-srt", required=True)
    parser.add_argument("--output-json", default="")
    parser.add_argument("--sample-fps", type=float, default=12.0, help="OCR sampling rate. 12fps catches most human-visible subtitle changes without native-frame OCR cost")
    parser.add_argument("--crop-top", type=float, default=0.65)
    parser.add_argument("--crop-bottom", type=float, default=0.98)
    parser.add_argument("--crop-left", type=float, default=0.05)
    parser.add_argument("--crop-right", type=float, default=0.98)
    parser.add_argument("--min-conf", type=float, default=0.18)
    parser.add_argument("--max-gap", type=float, default=0.28)
    parser.add_argument("--min-duration", type=float, default=0.12)
    parser.add_argument("--dedup-gap", type=float, default=1.0, help="merge duplicate/similar OCR cues separated by at most this many seconds")
    parser.add_argument("--start", type=float, default=0.0)
    parser.add_argument("--end", type=float, default=0.0, help="0 means until video end")
    parser.add_argument("--gpu", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    samples = extract_samples(args)
    cues = group_samples(samples, args.max_gap, args.min_duration)
    cues = merge_duplicate_cues(cues, args.dedup_gap)
    write_srt(cues, Path(args.output_srt))
    if args.output_json:
        Path(args.output_json).write_text(json.dumps({
            "samples": [s.__dict__ for s in samples],
            "cues": [c.__dict__ for c in cues],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "samples": len(samples), "cues": len(cues), "output_srt": args.output_srt}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
