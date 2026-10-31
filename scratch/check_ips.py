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
    cat /opt/etc/nfqws2/lists/ipset.list
    echo "=== Ping NNMClub IP 188.114.97.3 ==="
    ping -c 2 -W 2 188.114.97.3 || true
    echo "=== Ping Flibusta IP 179.43.150.83 ==="
    ping -c 2 -W 2 179.43.150.83 || true
    """
    stdin, stdout, stderr = client.exec_command(cmd)
    print(stdout.read().decode('utf-8', errors='replace'))
    client.close()

if __name__ == "__main__":
    run()
