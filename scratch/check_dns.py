import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')

HOST = "178.140.8.56"
PORT = 34222
USER = "root"
PASS = "keenetic"

def run_dns():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
    
    cmd = """
    echo "=== DNS Resolution ==="
    nslookup x.com
    nslookup twitter.com
    nslookup nnmclub.to
    nslookup flibusta.is
    echo "=== Ping / Route Check ==="
    ping -c 2 -W 2 1.1.1.1
    """
    stdin, stdout, stderr = client.exec_command(cmd)
    print(stdout.read().decode('utf-8', errors='replace'))
    client.close()

if __name__ == "__main__":
    run_dns()
