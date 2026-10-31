import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')

HOST = "178.140.8.56"
PORT = 34222
USER = "root"
PASS = "keenetic"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=12)

cmd = """
echo "=== 1. DHCP and Interface Home DNS config ==="
ndmc -c 'show interface Home' | grep -iE 'dns|address|dhcp' || true
ndmc -c 'show running-config' | grep -iE 'ip dhcp|name-server' || true

echo "=== 2. Detailed nslookup for chatgpt.com ==="
nslookup chatgpt.com 127.0.0.1
nslookup chatgpt.com 192.168.1.1

echo "=== 3. iptables NAT PREROUTING ==="
iptables -t nat -L PREROUTING -n -v --line-numbers

echo "=== 4. iptables mangle POSTROUTING (TCPMSS) ==="
iptables -t mangle -L POSTROUTING -n -v --line-numbers

echo "=== 5. iptables mangle PREROUTING ==="
iptables -t mangle -L PREROUTING -n -v --line-numbers

echo "=== 6. Test curl instagram and chatgpt from router ==="
curl -svo /dev/null --connect-timeout 5 https://www.instagram.com 2>&1 | head -n 25
curl -svo /dev/null --connect-timeout 5 https://chatgpt.com 2>&1 | head -n 25

echo "=== 7. What profiles match instagram in nfqws2.conf? ==="
grep -n -C 5 'instagram' /opt/etc/nfqws2/nfqws2.conf || true
"""

stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='replace'))
client.close()
