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
echo "=== 1. Check ppe ==="
ndmc -c 'show ppe' || true

echo "=== 2. Check interface Home ipv6 settings ==="
ndmc -c 'show running-config' | grep -iE 'interface Home|ipv6' || true

echo "=== 3. Check iptables FORWARD rules order ==="
iptables -L FORWARD -n -v --line-numbers | head -n 30
"""

stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='replace'))
client.close()
