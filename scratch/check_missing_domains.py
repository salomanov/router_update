import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')

HOST = "178.140.8.56"
PORT = 34222
USER = "root"
PASS = "keenetic"

def check_domains():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
    
    check_cmd = "grep -E '(^x\\.com$|^twitter\\.com$|nnmclub|kinozal|flibusta|telegram|chatgpt|openai)' /opt/etc/nfqws2/lists/user.list"
    stdin, stdout, stderr = client.exec_command(check_cmd)
    print("MATCHES IN user.list:")
    print(stdout.read().decode('utf-8', errors='replace'))
    
    check_auto = "grep -E '(^x\\.com$|^twitter\\.com$|nnmclub|kinozal|flibusta|telegram|chatgpt|openai)' /opt/etc/nfqws2/lists/auto.list"
    stdin, stdout, stderr = client.exec_command(check_auto)
    print("MATCHES IN auto.list:")
    print(stdout.read().decode('utf-8', errors='replace'))
    
    # Also check curl with verbose on x.com and nnmclub.to
    print("\n--- Detailed CURL x.com ---")
    stdin, stdout, stderr = client.exec_command("curl -svo /dev/null --connect-timeout 4 https://x.com 2>&1 | head -n 30")
    print(stdout.read().decode('utf-8', errors='replace'))

    print("\n--- Detailed CURL nnmclub.to ---")
    stdin, stdout, stderr = client.exec_command("curl -svo /dev/null --connect-timeout 4 https://nnmclub.to 2>&1 | head -n 30")
    print(stdout.read().decode('utf-8', errors='replace'))

    client.close()

if __name__ == "__main__":
    check_domains()
