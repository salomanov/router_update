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
echo "=== 1. Check IPV6 in Keenetic running config ==="
ndmc -c 'show running-config' | grep -i 'ipv6' || true

echo "=== 2. Check WAN IPv6 route ==="
ip -6 route

echo "=== 3. DNS query for google.com from remote router ==="
nslookup google.com 127.0.0.1

echo "=== 4. Check NFQWS2 config for google ==="
grep -i 'google' /opt/etc/nfqws2/nfqws2.conf
grep -i 'google' /opt/etc/nfqws2/lists/* 2>/dev/null || true

echo "=== 5. Check if nfqws2 is filtering google.com ==="
tail -n 30 /opt/var/log/nfqws2.log | grep -i 'google' || true

echo "=== 6. Test curl to google from remote router with -4 and -6 ==="
curl -4 -svo /dev/null --connect-timeout 4 https://www.google.com 2>&1 | head -n 15
curl -6 -svo /dev/null --connect-timeout 4 https://www.google.com 2>&1 | head -n 15 || true
"""
stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='replace'))
client.close()
