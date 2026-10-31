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
    
    cmds = {
        "grep_client_in_nfqws": "grep '172.16.2.33' /opt/var/log/nfqws2.log | tail -n 20",
        "conntrack_google": "grep '172.16.2.33' /proc/net/nf_conntrack | grep -i '443\\|googlevideo\\|youtube'",
        "policy_check": "ndmq -p 'show ip policy' -x 2>/dev/null || true",
        "l2tp_policy": "ndmq -p 'show interface L2tpServer0' -x 2>/dev/null || true"
    }
    
    for name, cmd in cmds.items():
        print(f"\n=================== {name} ===================")
        stdin, stdout, stderr = client.exec_command(cmd)
        print(stdout.read().decode('utf-8', errors='replace'))
    
    client.close()

if __name__ == "__main__":
    run()
