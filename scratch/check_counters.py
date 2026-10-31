import paramiko
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

HOST = "178.140.8.56"
PORT = 34222
USER = "root"
PASS = "keenetic"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=12)

cmd = """
echo "=== 1. Check packet counters on new rules ==="
iptables -t nat -L PREROUTING -n -v | grep -E 'br0.*53'
iptables -L FORWARD -n -v | grep -E 'br0'
ip6tables -L FORWARD -n -v | grep -E 'br0'
iptables -t mangle -L FORWARD -n -v | grep -i 'clamp'

echo "=== 2. Check recent conntrack for laptop 192.168.1.36 ==="
grep '192.168.1.36' /proc/net/nf_conntrack | tail -n 15 || true
"""

stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='replace'))
client.close()
