import requests
import json

url = "https://www.douyin.com/video/7641844145761340722"
tikwm_url = "https://www.tikwm.com/api/"

r = requests.post(tikwm_url, data={"url": url}, timeout=15)
print("Status:", r.status_code)
data = r.json()
print(json.dumps(data, indent=2, ensure_ascii=False))

if data.get("code") == 0:
    d = data.get("data", {})
    video_url = d.get("play")
    if video_url:
        if video_url.startswith("/"):
            video_url = "https://www.tikwm.com" + video_url
        print("\nVideo URL:", video_url)
        
        # Download
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        v = requests.get(video_url, headers=headers, stream=True, timeout=30)
        print("Video status:", v.status_code)
        if v.status_code == 200:
            with open("douyin_video.mp4", "wb") as f:
                for chunk in v.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
            print("Saved douyin_video.mp4")
        else:
            print("Failed to download video")