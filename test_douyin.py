import requests
import re
import json

def get_douyin_video(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.douyin.com/",
    }
    
    # 1. Lấy redirect URL nếu là link rút gọn, hoặc parse ID trực tiếp
    video_id = re.search(r'video/(\d+)', url)
    if not video_id:
        print("Không tìm thấy video ID")
        return
    video_id = video_id.group(1)
    print(f"Video ID: {video_id}")
    
    # Dùng API công khai lấy chi tiết video
    api_url = f"https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids={video_id}"
    
    response = requests.get(api_url, headers=headers)
    print(f"Status API 1: {response.status_code}")
    try:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
    except Exception as e:
        print(f"Lỗi parse JSON API 1: {e}")
        
    # Thử API thứ hai
    api_url_2 = f"https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id={video_id}"
    
    # Đọc cookies nếu có
    cookies = {}
    try:
        with open("www.douyin.com_30-06-2026.json", "r") as f:
            c_list = json.load(f)
            for c in c_list:
                cookies[c["name"]] = c["value"]
    except Exception as e:
        print(f"Lỗi đọc cookies: {e}")
        
    response_2 = requests.get(api_url_2, headers=headers, cookies=cookies)
    print(f"Status API 2: {response_2.status_code}")
    try:
        data2 = response_2.json()
        print("API 2 Response:")
        # Lưu ra file test
        with open("douyin_api_response.json", "w", encoding="utf-8") as f:
            json.dump(data2, f, indent=4, ensure_ascii=False)
        print("Đã ghi thông tin API 2 vào douyin_api_response.json")
    except Exception as e:
        print(f"Lỗi parse JSON API 2: {e}")

if __name__ == "__main__":
    get_douyin_video("https://www.douyin.com/video/7641844145761340722")
