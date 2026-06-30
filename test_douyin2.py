"""
Test douyin download using custom approach:
- Parse video HTML to get video URL
- Fallback: use public API with X-Bogus
"""

import requests
import re
import json

def main():
    url = "https://www.douyin.com/video/7641844145761340722"
    
    cookies = {}
    try:
        with open("www.douyin.com_30-06-2026.json", "r") as f:
            data = json.load(f)
            c_list = data if isinstance(data, list) else data.get("cookies", [])
            for c in c_list:
                cookies[c.get("name")] = c.get("value", "")
    except Exception as e:
        print(f"Cookie load: {e}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Referer": "https://www.douyin.com/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "vi,en;q=0.9",
    }
    
    resp = requests.get(url, headers=headers, cookies=cookies, timeout=15)
    print(f"HTML status: {resp.status_code}, len={len(resp.text)}")
    
    # Tìm video URL trong HTML
    # Douyin thường nhúng JSON-LD hoặc script có video_url
    patterns = [
        r'play_addr.*?url_list.*?\["([^"]+)"',
        r'"video".*?"play_addr".*?"url_list"\s*:\s*\["([^"]+)"',
        r'"srcUrl"\s*:\s*"([^"]+)"',
        r'"main_url"\s*:\s*"([^"]+)"',
        r'<video[^>]*src="([^"]+)"',
        r'video_id["\']?\s*:\s*["\']?([^"\'}\s,]+)',
    ]
    
    for p in patterns:
        m = re.search(p, resp.text, re.DOTALL)
        if m:
            print(f"Pattern \"{p[:30]}...\": {m.group(1)[:100]}")
            
    # Check for window.__data__
    script_match = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text, re.DOTALL)
    if script_match:
        try:
            data = json.loads(script_match.group(1))
            print("NEXT_DATA found")
            # extract video info
            video_data = data.get("props", {}).get("pageProps", {})
            with open("douyin_next_data.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("Saved NEXT_DATA to douyin_next_data.json")
            print("Keys:", list(video_data.keys())[:10])
        except Exception as e:
            print(f"Parse NEXT_DATA: {e}")

    # Check SSR data pattern
    ssr_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', resp.text, re.DOTALL)
    if ssr_match:
        try:
            ssr_data = json.loads(ssr_match.group(1))
            with open("douyin_initial_state.json", "w", encoding="utf-8") as f:
                json.dump(ssr_data, f, indent=2, ensure_ascii=False)
            print("Saved INITIAL_STATE to douyin_initial_state.json")
        except Exception as e:
            print(f"Parse INITIAL_STATE: {e}")
    
    # Debug: viết HTML ra file
    with open("douyin_page.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    print("Saved HTML to douyin_page.html")
            
if __name__ == "__main__":
    main()
