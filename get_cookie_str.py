import json

with open("www.douyin.com_30-06-2026.json", "r") as f:
    data = json.load(f)

cookies = data if isinstance(data, list) else data.get("cookies", [])
cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

with open("cookie_string.txt", "w") as f:
    f.write(cookie_str)
print("Cookie string saved")
