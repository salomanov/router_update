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
echo "=== 1. What is 37.230.192.51? ==="
nslookup 37.230.192.51 127.0.0.1 || true

echo "=== 2. Check iptables nat chains _NDM_DNS_FLT_REDIR, _NDM_IC_REDIRECT ==="
iptables -t nat -L _NDM_DNS_FLT_REDIR -n -v --line-numbers || true
iptables -t nat -L _NDM_IC_REDIRECT -n -v --line-numbers || true

echo "=== 3. Check /etc/resolv.conf and ndnproxy config ==="
cat /etc/resolv.conf || true
cat /opt/etc/resolv.conf || true
ps | grep -iE 'dns|ndnproxy|dns-proxy' || true

echo "=== 4. Check DHCP offer details for Home ==="
ndmc -c 'show ip dhcp pool _WEBADMIN' || true
"""

stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='replace'))
client.close()
