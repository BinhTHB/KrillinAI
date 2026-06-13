"""Fix SRT timing: truncate overly long subtitle spans and resolve overlapping entries.

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
    
    # Calculate total video duration from original file
    video_duration = entries[-1][1] if entries else 0

    # Ensure no overlap and no duplicate start times
    fixed = []
    occupied_slots = []  # (start, end) slots for overlap detection
    min_gap = 0.2  # 200ms minimum gap between subtitles
    
    for i, (start, orig_end, text, idx) in enumerate(entries):
        # Estimate reasonable duration based on text
        est_duration = estimate_duration(text)
        
        # Cap extremely long original durations
        if orig_end - start > 30:
            orig_end = start + min(8.0, est_duration * 1.5)
        
        # Determine available space
        next_start = entries[i + 1][0] if i + 1 < len(entries) else video_duration
        
        # Find a suitable start time that doesn't overlap existing slots
        candidate_start = start
        
        # Check for overlap with existing slots
        max_attempts = 100
        for attempt in range(max_attempts):
            overlap = False
            for slot_start, slot_end in occupied_slots:
                if candidate_start < slot_end and candidate_start + 0.5 > slot_start:
                    # Overlaps, shift forward
                    candidate_start = slot_end + min_gap
                    overlap = True
                    break
            
            # Also check if too close to next entry
            if candidate_start + est_duration > next_start - min_gap:
                candidate_start = next_start - min_gap - est_duration
                if candidate_start < start:
                    candidate_start = start
                    # Shorten duration to fit
                    est_duration = max(0.5, next_start - min_gap - candidate_start)
                    # If still too long, cap it
                    if est_duration < 0.5:
                        est_duration = 0.5
            
            if not overlap:
                break
        else:
            # If still overlapping after max attempts, force position after last slot
            if occupied_slots:
                last_slot_end = max(slot_end for slot_start, slot_end in occupied_slots)
                candidate_start = last_slot_end + min_gap
        
        # Ensure minimum gap from previous end if any
        if occupied_slots:
            last_end = max(slot_end for slot_start, slot_end in occupied_slots)
            if candidate_start < last_end + min_gap:
                candidate_start = last_end + min_gap
        
        # Calculate maximum possible end time
        max_end = min(next_start - min_gap, candidate_start + 8.0)  # cap at 8s max
        
        # Calculate desired duration
        desired_duration = min(est_duration, orig_end - start, 8.0)
        
        # Ensure minimum duration
        if desired_duration < 0.8 and est_duration > 0.8:
            desired_duration = min(0.8, max_end - candidate_start)
        
        # Adjust if exceeds next entry
        if candidate_start + desired_duration > max_end:
            desired_duration = max_end - candidate_start
            if desired_duration < 0.5:
                desired_duration = 0.5
        
        new_end = candidate_start + desired_duration
        
        # Add to occupied slots
        occupied_slots.append((candidate_start, new_end))
        
        fixed.append((candidate_start, new_end, text, idx))
    
    # If coverage is too short, extend later entries proportionally
    if fixed and video_duration > 0:
        coverage_end = fixed[-1][1]
        if coverage_end < video_duration * 0.7:
            # Need to extend coverage
            target_coverage = min(video_duration * 0.95, coverage_end * 1.3)
            extension_factor = target_coverage / coverage_end
            
            # Apply extension to entries after midpoint
            adjusted = []
            midpoint_idx = len(fixed) // 2
            
            for i, (start, end, text, idx) in enumerate(fixed):
                if i >= midpoint_idx:
                    # Extend later entries
                    duration = end - start
                    new_duration = duration * extension_factor
                    new_duration = min(new_duration, 8.0)
                    new_end = start + new_duration
                    
                    # Ensure no overlap with next
                    if i + 1 < len(fixed):
                        next_start = fixed[i + 1][0]
                        if new_end > next_start - min_gap:
                            new_end = next_start - min_gap
                    
                    adjusted.append((start, new_end, text, idx))
                else:
                    adjusted.append((start, end, text, idx))
            
            fixed = adjusted

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
    short_entries = sum(1 for s, e, _, _ in fixed if e - s < 0.5)
    coverage = fixed[-1][1] - fixed[0][0] if fixed else 0
    print(f"  Entries >30s remaining: {long_entries}")
    print(f"  Entries <0.5s remaining: {short_entries}")
    print(f"  Coverage: {coverage:.1f}s (video: {video_duration:.1f}s)")
    print(f"  Coverage ratio: {coverage/video_duration*100:.1f}%" if video_duration > 0 else "  No video duration")


if __name__ == '__main__':
    workdir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('./tasks/douyin-test')
    for name in ['origin_language_srt.srt', 'target_language_srt.srt']:
        src = workdir / name
        dst = workdir / name.replace('.srt', '_fixed.srt')
        if src.exists():
            fix_srt(src, dst)
        else:
            print(f"Skip {src}: not found")