import re

with open('douyin_page.html', 'r', encoding='utf-8') as f:
    html = f.read()

patterns = [
    r'play_addr.*?url_list.*?\["([^"]+)"',
    r'"video".*?"play_addr".*?"url_list"\s*:\s*\["([^"]+)"',
    r'"srcUrl"\s*:\s*"([^"]+)"',
    r'"main_url"\s*:\s*"([^"]+)"',
    r'<video[^>]*src="([^"]+)"',
    r'video_id["\']?\s*:\s*["\']?([^"\'}\s,]+)',
    r'\\"play_addr\\":.*?\\"url_list\\":.*?\\"([^\\"]+)\\"',
]

for p in patterns:
    matches = re.findall(p, html, re.DOTALL)
    if matches:
        print(f'Pattern: {p[:50]}')
        for m in matches[:3]:
            print(f'  -> {m[:120]}')
        print()