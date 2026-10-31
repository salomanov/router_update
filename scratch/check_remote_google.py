import paramiko
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

HOST = "178.140.8.56"
PORT = 34222
USER = "root"
PASS = "keenetic"

print(f"Подключение к удалённому роутеру {HOST}:{PORT}...")

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=12)
    print("SSH подключение успешно!\n")
except Exception as e:
    print(f"Ошибка подключения по SSH: {e}")
    sys.exit(1)

commands = {
    "1. Базовый пинг интернета (IP)": "ping -c 2 -W 2 1.1.1.1; ping -c 2 -W 2 8.8.8.8",
    "2. Проверка DNS резолвинга": "nslookup google.com; nslookup ya.ru; nslookup youtube.com",
    "3. Статус dns-proxy Keenetic": "ndmc -c 'show dns-proxy' 2>/dev/null | grep -A 25 'DNS Servers' || true",
    "4. Статус службы nfqws2": "/opt/etc/init.d/S51nfqws2 status; ps | grep nfqws2 | grep -v grep",
    "5. Тест curl Google (HTTP/HTTPS)": "curl -svo /dev/null --connect-timeout 5 https://www.google.com 2>&1 | head -n 30",
    "6. Тест curl YouTube": "curl -svo /dev/null --connect-timeout 5 https://www.youtube.com 2>&1 | head -n 25",
    "7. Тест curl Яндекс": "curl -svo /dev/null --connect-timeout 5 https://ya.ru 2>&1 | head -n 20",
    "8. Последние ошибки в логах nfqws2": "tail -n 25 /opt/var/log/nfqws2.log",
    "9. Состояние L2TP клиентов": "ifconfig | grep -A 5 'l2tp'; grep '172.16.2' /proc/net/nf_conntrack | tail -n 10 || true"
}

for title, cmd in commands.items():
    print(f"\n=================== {title} ===================")
    print(f"$ {cmd}")
    try:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=20)
        out = stdout.read().decode('utf-8', errors='replace')
        err = stderr.read().decode('utf-8', errors='replace')
        if out:
            print(out.strip())
        if err.strip():
            print(f"[STDERR]: {err.strip()}")
    except Exception as e:
        print(f"Ошибка выполнения команды: {e}")

client.close()
