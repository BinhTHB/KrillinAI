from dataclasses import dataclass
import re
from pathlib import Path

@dataclass
class SrtCue:
    index: int
    start: float
    end: float
    text: str

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


def parse_ts(ts: str) -> float:
    h, m, rest = ts.split(':')
    s, ms = rest.split(',')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


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


def load_srt(path: str | Path) -> list[SrtCue]:
    content = Path(path).read_text(encoding='utf-8-sig')
    blocks = re.split(r'\n\s*\n', content.strip())
    cues = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3:
            continue
        index = int(lines[0]) if lines[0].isdigit() else len(cues) + 1
        m = re.match(r'(\d\d:\d\d:\d\d,\d\d\d)\s+-->\s+(\d\d:\d\d:\d\d,\d\d\d)', lines[1])
        if not m:
            continue
        cues.append(SrtCue(index, parse_ts(m.group(1)), parse_ts(m.group(2)), '\n'.join(lines[2:])))
    return cues


def write_srt(cues: list[SrtCue], path: str | Path) -> None:
    out = []
    for i, cue in enumerate(cues, 1):
        out.append(str(i))
        out.append(f"{fmt_ts(cue.start)} --> {fmt_ts(cue.end)}")
        out.append(cue.text.strip())
        out.append("")
    Path(path).write_text('\n'.join(out), encoding='utf-8')
