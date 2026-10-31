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
echo "=== 1. DNS nslookup tests from router 127.0.0.1 ==="
nslookup gemini.google.com 127.0.0.1
nslookup www.instagram.com 127.0.0.1
nslookup chatgpt.com 127.0.0.1
nslookup www.youtube.com 127.0.0.1

echo "=== 2. Show dns-proxy full status ==="
ndmc -c 'show dns-proxy' | grep -A 30 'DNS Servers' || true

echo "=== 3. Check QUIC block rule packet counters in FORWARD ==="
iptables -L FORWARD -n -v | grep 443

echo "=== 4. Check conntrack for laptop 192.168.1.36 ==="
grep '192.168.1.36' /proc/net/nf_conntrack | tail -n 20 || true

echo "=== 5. Check nfqws2 log for recent events from 192.168.1.36 ==="
grep '192.168.1.36' /opt/var/log/nfqws2.log | tail -n 25 || true
"""
stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='replace'))
client.close()
