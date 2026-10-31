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
    echo "=== CURL chatgpt.com standard ==="
    curl -svo /dev/null --connect-timeout 5 https://chatgpt.com 2>&1 | head -n 30
    
    echo "=== CURL chatgpt.com resolved to GeoHide IP 5.175.161.3 ==="
    curl -svo /dev/null --connect-timeout 5 --resolve chatgpt.com:443:5.175.161.3 https://chatgpt.com 2>&1 | head -n 30
    """
    stdin, stdout, stderr = client.exec_command(cmd)
    print(stdout.read().decode('utf-8', errors='replace'))
    client.close()

if __name__ == "__main__":
    run()
