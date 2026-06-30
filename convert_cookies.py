import json
import time

def json_to_netscape(json_file, txt_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # data có thể là list cookie hoặc dict dạng { "cookies": [...] }
    cookies = data.get("cookies", data) if isinstance(data, dict) else data

    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("# Netscape HTTP Cookie File\n")
        f.write("# This is a generated file! Do not edit.\n\n")
        
        for cookie in cookies:
            domain = cookie.get("domain", "")
            # Netscape format: domain, flag, path, secure, expiration, name, value
            flag = "TRUE" if domain.startswith(".") else "FALSE"
            path = cookie.get("path", "/")
            secure = "TRUE" if cookie.get("secure", False) else "FALSE"
            
            # Xử lý expiration date
            exp = cookie.get("expirationDate")
            if exp is None:
                exp = int(time.time() + 30 * 24 * 3600)  # 30 days default
            else:
                exp = int(exp)
                
            name = cookie.get("name", "")
            value = cookie.get("value", "")
            
            f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{exp}\t{name}\t{value}\n")

if __name__ == "__main__":
    json_to_netscape("www.douyin.com_30-06-2026.json", "douyin_cookies.txt")
    print("Done")
