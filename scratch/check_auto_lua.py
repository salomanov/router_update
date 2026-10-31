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
echo "=== Check zapret-auto.lua profiles ==="
grep -A 20 -i 'profile' /opt/etc/nfqws2/lua/zapret-auto.lua | head -n 30 || true

echo "=== Check log for google.com ==="
grep -i 'google.com' /opt/var/log/nfqws2.log | tail -n 20

echo "=== Check what happens when curl google.com with SNI from LAN ==="
# Test with fake client Hello or check iptables ip6tables
ip6tables -L -n -v
"""
stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='replace'))
client.close()
