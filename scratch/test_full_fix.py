import paramiko
import sys
import urllib.request
import time

sys.stdout.reconfigure(encoding='utf-8')

LOCAL_HOST = "192.168.1.1"
PORT = 222
USER = "root"
PASS = "keenetic"

print("1. Adding crosspointreader.com to router's /etc/hosts...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(LOCAL_HOST, port=PORT, username=USER, password=PASS, timeout=5)

cmd = """
sed -i '/crosspointreader/d' /etc/hosts
echo "104.21.28.172 crosspointreader.com www.crosspointreader.com" >> /etc/hosts
killall -HUP ndnproxy 2>/dev/null || true
"""
client.exec_command(cmd)
client.close()

time.sleep(1)

print("\n2. Testing from local PC via urllib.request...")
try:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    req = urllib.request.Request("https://crosspointreader.com/", headers=headers)
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=5) as resp:
        dt = (time.time() - t0) * 1000
        print(f"УСПЕХ! Статус: {resp.status} {resp.reason} за {dt:.1f} мс!")
        print(f"Заголовки: Content-Type: {resp.headers.get('Content-Type')}, Server: {resp.headers.get('Server')}")
except Exception as e:
    print(f"Ошибка с ПК: {e}")
