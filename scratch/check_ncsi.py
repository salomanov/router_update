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
    echo "=== Ping 4.207.247.139 ==="
    ping -c 2 -W 2 4.207.247.139 || true
    echo "=== HTTP msftconnecttest ==="
    curl -svo /dev/null --connect-timeout 4 http://www.msftconnecttest.com/connecttest.txt 2>&1 | head -n 20
    echo "=== HTTPS msftconnecttest ==="
    curl -svo /dev/null --connect-timeout 4 https://www.msftconnecttest.com/connecttest.txt 2>&1 | head -n 20
    """
    stdin, stdout, stderr = client.exec_command(cmd)
    print(stdout.read().decode('utf-8', errors='replace'))
    client.close()

if __name__ == "__main__":
    run()
