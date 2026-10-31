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
    echo "=== nslookup chatgpt.com via 127.0.0.1 ==="
    nslookup chatgpt.com 127.0.0.1
    echo "=== ndmc show ip dns-proxy ==="
    ndmc -c 'show ip dns-proxy' || true
    echo "=== ndmc show ip name-server ==="
    ndmc -c 'show ip name-server' || true
    """
    stdin, stdout, stderr = client.exec_command(cmd)
    print(stdout.read().decode('utf-8', errors='replace'))
    client.close()

if __name__ == "__main__":
    run()
