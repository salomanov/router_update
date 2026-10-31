import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

for ip in ["37.230.192.51", "45.155.204.190"]:
    try:
        req = urllib.request.urlopen(f"https://ipinfo.io/{ip}/json", timeout=5)
        data = json.loads(req.read().decode())
        print(ip, "->", data.get("org"), "|", data.get("city"), "|", data.get("country"))
    except Exception as e:
        print(ip, "-> error:", e)
