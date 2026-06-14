import re
from pathlib import Path

workdir = Path('tasks/douyin-new')

with open(workdir / 'target_language_srt.srt', 'r', encoding='utf-8') as f:
    raw = f.read()

blocks = re.split(r'\n\n+', raw.strip())
texts = []
for b in blocks:
    lines = b.strip().split('\n')
    if len(lines) < 3: 
        texts.append('')
        continue
    text = '\n'.join(lines[2:]).strip()
    texts.append(text)

texts = [t for t in texts if t]
print(f'Total texts: {len(texts)}')

def format_time(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f'{h:02d}:{m:02d}:{s:06.3f}'.replace('.', ',')

total_chars = sum(len(t) for t in texts)
target_dur = 180.3
gap = 0.15

output = []
current_time = 0.0
for i, text in enumerate(texts):
    if not text.strip():
        continue
    entry_dur = max(1.0, len(text) / total_chars * target_dur)
    start = current_time
    end = start + entry_dur - gap
    start_str = format_time(start)
    end_str = format_time(end)
    output.append(f'{i+1}\n{start_str} --> {end_str}\n{text}')
    current_time = end + gap

print(f'Total duration: {current_time:.1f}s')

with open(workdir / 'target_language_srt_fixed.srt', 'w', encoding='utf-8') as f:
    f.write('\n\n'.join(output))
print('Saved target_language_srt_fixed.srt')
