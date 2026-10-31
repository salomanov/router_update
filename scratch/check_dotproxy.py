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
echo "=== /var/run/dotproxy-*.yml ==="
cat /var/run/dotproxy-0-1.yml
echo "--- 0-5 ---"
cat /var/run/dotproxy-0-5.yml

echo "=== ndmc show dns-proxy servers ==="
ndmc -c 'show dns-proxy'
"""

stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='replace'))
client.close()
