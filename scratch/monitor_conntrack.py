import paramiko
import sys
import time

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
    echo "=== TCPMSS hit counters ==="
    iptables -t mangle -L FORWARD -n -v | grep -i 'tcpmss\\|l2tp'
    echo "=== Conntrack Active YouTube / Google ==="
    grep '172.16.2.33' /proc/net/nf_conntrack | grep -E '443' | tail -n 15
    """
    stdin, stdout, stderr = client.exec_command(cmd)
    print(stdout.read().decode('utf-8', errors='replace'))
    client.close()

if __name__ == "__main__":
    run()
