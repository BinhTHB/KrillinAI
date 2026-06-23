from dataclasses import dataclass
from srt_utils import SrtCue

@dataclass
class CueBudget:
    index: int
    cue_start: float
    cue_end: float
    allowed_start: float
    allowed_end: float
    allowed_duration: float
    cue_duration: float
    max_chars: int


def estimate_max_chars(duration: float, chars_per_second: float = 13.0) -> int:
    return max(4, int(duration * chars_per_second))


def build_budgets(
    cues: list[SrtCue],
    pre_roll: float = 0.15,
    post_roll: float = 0.65,
    min_gap_before_next: float = 0.12,
    chars_per_second: float = 13.0,
) -> list[CueBudget]:
    budgets: list[CueBudget] = []
    prev_voice_end = 0.0
    for i, cue in enumerate(cues):
        next_start = cues[i + 1].start if i + 1 < len(cues) else cue.end + post_roll
        allowed_start = max(prev_voice_end, cue.start - pre_roll)
        allowed_end = min(next_start - min_gap_before_next, cue.end + post_roll)
        if allowed_end <= allowed_start:
            allowed_start = cue.start
            allowed_end = cue.end
        allowed_duration = max(0.05, allowed_end - allowed_start)
        budgets.append(CueBudget(
            index=cue.index,
            cue_start=cue.start,
            cue_end=cue.end,
            allowed_start=allowed_start,
            allowed_end=allowed_end,
            allowed_duration=allowed_duration,
            cue_duration=cue.duration,
            max_chars=estimate_max_chars(allowed_duration, chars_per_second),
        ))
        prev_voice_end = allowed_start
    return budgets
