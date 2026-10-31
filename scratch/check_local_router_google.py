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
    echo "=== Ping from local router ==="
    ping -c 2 1.1.1.1
    ping -c 2 8.8.8.8
    echo "=== DNS from local router ==="
    nslookup google.com
    echo "=== Curl google from local router ==="
    curl -svo /dev/null --connect-timeout 4 https://www.google.com 2>&1 | head -n 25
    echo "=== Check nfqws2 status on local router ==="
    /opt/etc/init.d/S51nfqws2 status 2>/dev/null || ps | grep nfqws
    """
    stdin, stdout, stderr = client.exec_command(cmd)
    print(stdout.read().decode('utf-8', errors='replace'))
    client.close()
except Exception as e:
    print(f"Error connecting to local router: {e}")
