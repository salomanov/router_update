import paramiko
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

HOST = "178.140.8.56"
PORT = 34222
USER = "root"
PASS = "keenetic"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=12)

cmd = """
echo "=== 1. Удаление 1.1.1.1 и 77.88.8.8 из dns-proxy ==="
ndmc -c 'no dns-proxy https upstream https://1.1.1.1/dns-query'
ndmc -c 'no dns-proxy https upstream https://77.88.8.8/dns-query'
ndmc -c 'system configuration save'

echo "=== 2. Перезапуск ndnproxy (сброс кэша) ==="
killall ndnproxy 2>/dev/null || true
sleep 2

echo "=== 3. Проверка резолвинга chatgpt.com (должен вернуться GeoHide/Xbox IP) ==="
nslookup chatgpt.com 127.0.0.1

echo "=== 4. Проверка резолвинга google.com ==="
nslookup google.com 127.0.0.1

echo "=== 5. Тест curl chatgpt.com ==="
curl -svo /dev/null --connect-timeout 5 https://chatgpt.com 2>&1 | grep -E 'HTTP/|Connected|Server:' || true

echo "=== 6. Тест curl google.com ==="
curl -svo /dev/null --connect-timeout 4 https://www.google.com 2>&1 | grep -E 'HTTP/|Connected' || true
"""
stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='replace'))
client.close()
