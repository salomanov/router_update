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
echo "=== Current active interfaces on remote router ==="
ip link show | grep -E '^[0-9]+:'
echo "=== Check if l2tp or ppp exists ==="
ip addr show | grep -E 'l2tp|ppp|172.16' || echo "NO L2TP INTERFACE PRESENT"
echo "=== Check recent connections in conntrack ==="
grep '172.16.2' /proc/net/nf_conntrack | tail -n 15 || echo "NO 172.16.2 CONNECTIONS"
"""
stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='replace'))
client.close()
