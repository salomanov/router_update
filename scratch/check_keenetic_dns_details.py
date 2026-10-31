import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')

HOST = "178.140.8.56"
PORT = 34222
USER = "root"
PASS = "keenetic"

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
    
    cmd = """
    echo "=== Full dns-proxy config ==="
    ndmc -c 'show running-config' | grep -A 30 'dns-proxy'
    
    echo "=== Show ip name-server / show dns-proxy ==="
    ndmc -c 'show dns-proxy' 2>/dev/null || true
    ndmc -c 'show ip hotspot' 2>/dev/null | grep -E 'dns|policy' | head -n 20 || true
    
    echo "=== Check dnsm object or policy ==="
    ndmc -c 'show running-config' | grep -i 'dnsm' || true
    ndmc -c 'show running-config' | grep -i 'policy' | head -n 30 || true
    """
    stdin, stdout, stderr = client.exec_command(cmd)
    print(stdout.read().decode('utf-8', errors='replace'))
    client.close()

if __name__ == "__main__":
    run()
