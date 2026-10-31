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
echo "=== Search nfqws2.log for chatgpt.com or 179.254.166.174 ==="
grep -E 'chatgpt|179\.254\.166\.174' /opt/var/log/nfqws2.log || true
grep -E 'chatgpt|179\.254\.166\.174' /opt/var/log/nfqws2-debug.log 2>/dev/null || true
"""

stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='replace'))
client.close()
