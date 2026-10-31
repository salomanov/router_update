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
echo "=== 1. Active nfqws process ==="
ps | grep nfqws | grep -v grep

echo "=== 2. List sizes in /opt/etc/nfqws2/lists/ ==="
wc -l /opt/etc/nfqws2/lists/* 2>/dev/null || true

echo "=== 3. Current nfqws2.conf ==="
cat /opt/etc/nfqws2/nfqws2.conf | grep -iE 'NFQWS_ARGS|MODE|auto.list' | head -n 20
"""

stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='replace'))
client.close()
