"""Fix SRT timing: truncate overly long subtitle spans.

whispercpp ASR sometimes produces entries spanning entire video
duration (e.g. 00:00:02 -> 00:04:57). This script replaces those
spans with reasonable estimates based on text length.
"""
import re
import sys
from pathlib import Path


def srt_time_to_sec(t):
    h, m, s = t.replace(',', '.').split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)


def sec_to_srt_time(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace('.', ',')


def estimate_duration(text, min_s=1.5, max_s=8.0, char_rate=0.2):
    """Estimate spoken duration from text length."""
    text = text.strip()
    if not text:
        return min_s
    # Count actual characters (handle CJK + latin mixed)
    n = len(text)
    dur = n * char_rate
    return max(min_s, min(max_s, dur))


def fix_srt(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    blocks = re.split(r'\n\n+', content.strip())
    entries = []

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        # Parse index
        try:
            idx = int(lines[0].strip())
        except ValueError:
            continue
        # Parse time range
        m = re.match(r'(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3})', lines[1])
        if not m:
            continue
        start_str, end_str = m.group(1), m.group(2)
        start = srt_time_to_sec(start_str)
        end = srt_time_to_sec(end_str)
        text = '\n'.join(lines[2:])
        entries.append((start, end, text, idx))

    # Sort by start time, then end time
    entries.sort(key=lambda e: (e[0], e[1]))

    # Fix each entry
    fixed = []
    for i, (start, orig_end, text, idx) in enumerate(entries):
        # Estimate reasonable duration
        est = estimate_duration(text)

        # Clamp to not overlap with next entry's start
        if i + 1 < len(entries):
            next_start = entries[i + 1][0]
            max_end = next_start - 0.1  # 100ms gap
        else:
            max_end = orig_end  # keep original for last entry

        # Also cap at original duration
        new_duration = min(est, orig_end - start)
        # But not more than available space
        new_duration = min(new_duration, max(0.5, max_end - start))

        new_end = start + new_duration
        fixed.append((start, new_end, text, idx))

    # Build output
    out_lines = []
    for i, (start, end, text, idx) in enumerate(fixed):
        out_lines.append(str(idx))
        out_lines.append(f"{sec_to_srt_time(start)} --> {sec_to_srt_time(end)}")
        out_lines.append(text)
        out_lines.append('')

    output_path.write_text('\n'.join(out_lines), encoding='utf-8')
    print(f"Fixed {len(fixed)} entries: {input_path} -> {output_path}")

    # Stats
    long_entries = sum(1 for s, e, _, _ in fixed if e - s > 30)
    print(f"  Entries >30s remaining: {long_entries}")
    print(f"  Total duration: {fixed[-1][1] - fixed[0][0]:.1f}s" if fixed else "  No entries")


if __name__ == '__main__':
    workdir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('./tasks/douyin-test')
    for name in ['origin_language_srt.srt', 'target_language_srt.srt']:
        src = workdir / name
        dst = workdir / name.replace('.srt', '_fixed.srt')
        if src.exists():
            fix_srt(src, dst)
        else:
            print(f"Skip {src}: not found")
