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
    echo "=== Active connections from 172.16.2.33 ==="
    grep '172.16.2.33' /proc/net/nf_conntrack | tail -n 25
    echo "=== IPv6 Conntrack ==="
    grep -i 'ipv6' /proc/net/nf_conntrack | head -n 10 || true
    echo "=== WAN IPv6 Status ==="
    ip -6 route
    """
    stdin, stdout, stderr = client.exec_command(cmd)
    print(stdout.read().decode('utf-8', errors='replace'))
    client.close()

if __name__ == "__main__":
    run()
