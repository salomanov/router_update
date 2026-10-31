import sys
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

res = subprocess.run(["ipconfig", "/all"], capture_output=True, text=True, errors='replace')
for line in res.stdout.splitlines():
    if any(k in line.lower() for k in ["dns servers", "dns-сервер", "основной шлюз", "default gateway", "ethernet", "wi-fi", "адаптер"]):
        print(line)
