import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')

LOCAL_HOST = "192.168.1.1"
PORT = 222
USER = "root"
PASS = "keenetic"

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(LOCAL_HOST, port=PORT, username=USER, password=PASS, timeout=5)
    print("Connected to local router 192.168.1.1:222!")
    
    cmd = """
    nslookup crosspointreader.com 127.0.0.1
    ndmc -c 'show running-config' | grep -i 'crosspoint' || true
    ndmc -c 'show dns-proxy' 2>/dev/null | grep -A 20 -i 'DNS Servers' || true
    """
    stdin, stdout, stderr = client.exec_command(cmd)
    print(stdout.read().decode('utf-8', errors='replace'))
    client.close()
except Exception as e:
    print(f"SSH to local router error: {e}")
