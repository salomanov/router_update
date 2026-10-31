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
echo "=== Hotspot host list on remote router ==="
ndmc -c 'show ip hotspot' | grep -E 'hostname|ip|mac|interface|active' | head -n 40
echo "=== L2TP Server Status ==="
ndmc -c 'show crypto map VPNL2TPServer' || true
echo "=== VPN connections ==="
ndmc -c 'show vpn-server' || true
"""
stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='replace'))
client.close()
