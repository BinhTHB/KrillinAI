import requests
import json

def test_api():
    url = "https://www.douyin.com/video/7641844145761340722"
    api_url = f"https://api.douyin.wtf/api?url={url}"
    
    try:
        r = requests.get(api_url, timeout=15)
        print("wtf status:", r.status_code)
        data = r.json()
        if data.get("status") == "success" or "video_data" in data:
            print("WTF API Success!")
            # Print video info
            video_url = data.get("video_data", {}).get("nwm_video_url_HQ") or data.get("video_data", {}).get("nwm_video_url")
            print("No Watermark Video HQ:", video_url)
            return
    except Exception as e:
        print("WTF API Error:", e)

    # Thử API khác: hybrid-analysis / tikhub hoặc api củatikwm
    tikwm_url = "https://www.tikwm.com/api/"
    try:
        r = requests.post(tikwm_url, data={"url": url}, timeout=15)
        print("tikwm status:", r.status_code)
        data = r.json()
        if data.get("code") == 0:
            print("TikWM Success!")
            # data['data']['play'] là link no watermark
            print("No Watermark Video:", data.get("data", {}).get("play"))
            # data['data']['music'] là link nhạc
            print("Music:", data.get("data", {}).get("music"))
            
            # Tải video về
            video_dl_url = "https://www.tikwm.com" + data["data"]["play"] if data["data"]["play"].startswith("/") else data["data"]["play"]
            print("Downloading from:", video_dl_url)
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            v_resp = requests.get(video_dl_url, headers=headers, stream=True)
            if v_resp.status_code == 200:
                with open("douyin_video.mp4", "wb") as f:
                    for chunk in v_resp.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)
                print("Tải video thành công: douyin_video.mp4")
            else:
                print("Lỗi tải file video:", v_resp.status_code)
            return
    except Exception as e:
        print("TikWM API Error:", e)

if __name__ == "__main__":
    test_api()
