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
    iptables -L FORWARD -n -v --line-numbers
    echo "=== _NDM_FORWARD ==="
    iptables -L _NDM_FORWARD -n -v --line-numbers
    echo "=== _NDM_VPN_FORWARD ==="
    iptables -L _NDM_VPN_FORWARD -n -v --line-numbers
    """
    stdin, stdout, stderr = client.exec_command(cmd)
    print(stdout.read().decode('utf-8', errors='replace'))
    client.close()

if __name__ == "__main__":
    run()
