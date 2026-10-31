import paramiko
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

HOST = "178.140.8.56"
PORT = 34222
USER = "root"
PASS = "keenetic"

print(f"Подключение к удалённому роутеру {HOST}:{PORT} для исправления сети...")

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=12)

# --- ШАГ 1: Отключение IPv6 на локальной сети (устранение черной дыры Happy Eyeballs) ---
print("\n[1/5] Отключение неработающего IPv6 на интерфейсе Home (br0)...")
ipv6_cmds = """
ndmc -c 'no ipv6 subnet Default'
ndmc -c 'system configuration save'
"""
stdin, stdout, stderr = client.exec_command(ipv6_cmds)
print(stdout.read().decode('utf-8', errors='replace'))

# Также сбросим IPv6 маршрутизацию и RA объявления для LAN
client.exec_command("echo 0 > /proc/sys/net/ipv6/conf/br0/accept_ra 2>/dev/null || true")

# --- ШАГ 2: Исключение google.com из десинхронизации nfqws2 ---
print("\n[2/5] Очистка google.com из auto.list и добавление в exclude.list...")
fix_lists_cmd = """
# Удаляем google.com и www.google.com из auto.list
sed -i '/^google\\.com$/d' /opt/etc/nfqws2/lists/auto.list
sed -i '/^www\\.google\\.com$/d' /opt/etc/nfqws2/lists/auto.list
sed -i '/^play\\.google\\.com$/d' /opt/etc/nfqws2/lists/auto.list

# Гарантируем, что google.com в exclude.list (чтобы поиск и сервисы шли напрямую без десинхронизации)
for d in google.com www.google.com google.ru www.google.ru; do
    grep -q "^$d$" /opt/etc/nfqws2/lists/exclude.list || echo "$d" >> /opt/etc/nfqws2/lists/exclude.list
done

echo "Записи в exclude.list для google:"
grep -i 'google' /opt/etc/nfqws2/lists/exclude.list
"""
stdin, stdout, stderr = client.exec_command(fix_lists_cmd)
print(stdout.read().decode('utf-8', errors='replace'))

# --- ШАГ 3: Добавление резервных стабильных DNS серверов в Keenetic ---
print("\n[3/5] Проверка и усиление DNS апстримов в Keenetic...")
dns_cmd = """
# Добавляем прямой Cloudflare DoH и обычные fallback DNS если DoH оператора сбоит
ndmc -c 'dns-proxy https upstream https://1.1.1.1/dns-query' 2>/dev/null || true
ndmc -c 'dns-proxy https upstream https://77.88.8.8/dns-query' 2>/dev/null || true
ndmc -c 'system configuration save'
"""
stdin, stdout, stderr = client.exec_command(dns_cmd)
print(stdout.read().decode('utf-8', errors='replace'))

# --- ШАГ 4: Перезапуск nfqws2 ---
print("\n[4/5] Перезапуск службы nfqws2...")
restart_cmd = "/opt/etc/init.d/S51nfqws2 restart"
stdin, stdout, stderr = client.exec_command(restart_cmd)
print(stdout.read().decode('utf-8', errors='replace'))

time.sleep(2)

# --- ШАГ 5: Проверка результатов ---
print("\n[5/5] Контрольная проверка доступности Google и сайтов...")
test_cmd = """
echo "=== 1. Проверка IPv6 в конфиге Keenetic ==="
ndmc -c 'show running-config' | grep -i 'ipv6 subnet' || echo "IPv6 subnet отключен (OK)"

echo "=== 2. Проверка DNS резолвинга google.com ==="
nslookup google.com 127.0.0.1

echo "=== 3. Проверка HTTP/HTTPS ответа google.com ==="
curl -svo /dev/null --connect-timeout 4 https://www.google.com 2>&1 | head -n 25

echo "=== 4. Проверка YouTube ==="
curl -svo /dev/null --connect-timeout 4 https://www.youtube.com 2>&1 | head -n 25

echo "=== 5. Проверка nfqws2 status ==="
/opt/etc/init.d/S51nfqws2 status
"""
stdin, stdout, stderr = client.exec_command(test_cmd)
print(stdout.read().decode('utf-8', errors='replace'))

client.close()
print("\nГотово!")
