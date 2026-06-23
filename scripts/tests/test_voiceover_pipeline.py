#!/usr/bin/env python3
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from srt_utils import SrtCue, fmt_ts, parse_ts
from voiceover_budget import build_budgets, estimate_max_chars


def test_srt_cue_duration():
    cue = SrtCue(1, 1.0, 2.5, "Test")
    assert abs(cue.duration - 1.5) < 0.001


def test_fmt_ts_roundtrip():
    ts = "00:01:23,456"
    seconds = parse_ts(ts)
    back = fmt_ts(seconds)
    assert back == ts


def test_build_budgets_no_overlap():
    cues = [
        SrtCue(1, 0.0, 1.0, "A"),
        SrtCue(2, 2.0, 3.0, "B"),
    ]
    budgets = build_budgets(cues, pre_roll=0.15, post_roll=0.65, min_gap_before_next=0.12)
    assert budgets[0].allowed_end <= budgets[1].allowed_start


def test_estimate_max_chars():
    n = estimate_max_chars(2.0, chars_per_second=13.0)
    assert n == 26


def test_quality_gate_no_cjk():
    from voiceover_quality_gate import check_cjk
    assert not check_cjk("Xin chào")
    assert check_cjk("你好")


if __name__ == "__main__":
    test_srt_cue_duration()
    test_fmt_ts_roundtrip()
    test_build_budgets_no_overlap()
    test_estimate_max_chars()
    test_quality_gate_no_cjk()
    print("All tests passed.")
