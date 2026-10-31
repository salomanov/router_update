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
    ndmq -p 'show running-config' -x 2>/dev/null | grep -A 25 -i 'interface L2tpServer' || true
    """
    stdin, stdout, stderr = client.exec_command(cmd)
    print("RUNNING CONFIG L2TP:")
    print(stdout.read().decode('utf-8', errors='replace'))
    
    # Also check if ndm CLI has tcpmss command
    cmd2 = "ndmq -p 'show interface' -x 2>/dev/null | grep -B 2 -A 10 -i 'l2tp' || true"
    stdin, stdout, stderr = client.exec_command(cmd2)
    print("SHOW INTERFACE:")
    print(stdout.read().decode('utf-8', errors='replace'))

    client.close()

if __name__ == "__main__":
    run()
