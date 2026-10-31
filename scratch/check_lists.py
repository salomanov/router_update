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
echo "=== user.list ==="
cat /opt/etc/nfqws2/lists/user.list

echo "=== exclude.list ==="
cat /opt/etc/nfqws2/lists/exclude.list

echo "=== auto.list count and top 20 ==="
wc -l /opt/etc/nfqws2/lists/auto.list
head -n 20 /opt/etc/nfqws2/lists/auto.list
"""

stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='replace'))
client.close()
