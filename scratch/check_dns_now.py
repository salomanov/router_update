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
echo "=== DNS PROXY STATUS ==="
ndmc -c 'show dns-proxy' | grep -A 25 'DNS Servers' || true
echo "=== CURL TEST GOOGLE ==="
curl -svo /dev/null --connect-timeout 4 https://www.google.com 2>&1 | grep -E 'HTTP/|Connected'
echo "=== CURL TEST YOUTUBE ==="
curl -svo /dev/null --connect-timeout 4 https://www.youtube.com 2>&1 | grep -E 'HTTP/|Connected'
"""
stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='replace'))
client.close()
