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
echo "=== 1. _NDM_DNS_REDIRECT rules ==="
iptables -t nat -L _NDM_DNS_REDIRECT -n -v --line-numbers || true

echo "=== 2. Show ipv6 in Keenetic ==="
ndmc -c 'show ipv6 status' || true
ndmc -c 'show ipv6 prefix' || true
ndmc -c 'show ipv6 route' || true

echo "=== 3. Check if ip6tables is running ==="
ip6tables -L -n -v || true

echo "=== 4. Check /proc/sys/net/ipv6/conf/ ==="
cat /proc/sys/net/ipv6/conf/all/disable_ipv6
cat /proc/sys/net/ipv6/conf/default/disable_ipv6
cat /proc/sys/net/ipv6/conf/br0/disable_ipv6

echo "=== 5. Check TCPMSS on FORWARD and POSTROUTING ==="
iptables -L FORWARD -n -v | grep -i mss || true
iptables -t mangle -L FORWARD -n -v | grep -i mss || true
iptables -t mangle -L POSTROUTING -n -v | grep -i mss || true
"""

stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='replace'))
client.close()
