#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from srt_utils import load_srt

CJK_RE = re.compile(r'[\u3400-\u9fff]')


def get_duration(path: Path) -> float:
    result = subprocess.run(
        f'ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "{path}"',
        shell=True, capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def check_cjk(text: str) -> bool:
    return bool(CJK_RE.search(text))


def check_adjacent_duplicates(cues) -> int:
    count = 0
    for i in range(len(cues) - 1):
        nt = cues[i].text.strip()
        nn = cues[i + 1].text.strip()
        if nt and nt == nn:
            count += 1
    return count


def check_overlaps(cues) -> int:
    count = 0
    for i in range(len(cues) - 1):
        if cues[i].end > cues[i + 1].start + 0.05:
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description='Quality gate for subtitled TTS video.')
    parser.add_argument('--target-srt', required=True)
    parser.add_argument('--tts-report', default='')
    parser.add_argument('--video', default='')
    parser.add_argument('--output', default='')
    args = parser.parse_args()

    checks = {}
    target = load_srt(args.target_srt)

    checks['no_cjk'] = not any(check_cjk(c.text) for c in target)
    checks['no_empty_text'] = not any(not c.text.strip() for c in target)
    checks['no_negative_duration'] = not any(c.duration <= 0 for c in target)
    checks['near_duplicates'] = check_adjacent_duplicates(target) == 0
    checks['no_overlap'] = check_overlaps(target) == 0

    if args.tts_report:
        tts = json.loads(Path(args.tts_report).read_text(encoding='utf-8'))
        summary = tts.get('summary', {})
        checks['tts_no_rewrite_needed'] = summary.get('rewrite_needed', 0) == 0
        checks['tts_no_failed'] = summary.get('tts_failed', 0) == 0

    if args.video:
        dur = get_duration(Path(args.video))
        checks['video_exists'] = dur > 1.0
    else:
        checks['video_exists'] = True

    ok = all(checks.values())
    result = {'ok': ok, 'checks': checks}
    print(json.dumps(result, ensure_ascii=False))

    if args.output:
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

    if not ok:
        failed = [k for k, v in checks.items() if not v]
        print(f'FAILED checks: {failed}')
        sys.exit(1)


if __name__ == '__main__':
    import sys
    main()
