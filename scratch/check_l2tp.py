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
        "ifconfig_l2tp": "ifconfig | grep -A 6 'l2tp\\|ppp'",
        "ip_route": "ip route",
        "ip_rule": "ip rule",
        "iptables_forward": "iptables -L FORWARD -n -v",
        "iptables_mangle_tcpmss": "iptables -t mangle -L -n -v | grep -i 'tcpmss\\|mss\\|l2tp'",
        "iptables_udp_443": "iptables -L -n -v | grep 443",
        "iptables_mangle_udp_443": "iptables -t mangle -L -n -v | grep 443",
        "nfqws_log_tail": "tail -n 30 /opt/var/log/nfqws2.log",
        "keenetic_l2tp_clients": "ndmq -p 'show ip hotspot' -x 2>/dev/null || true"
    }
    
    for name, cmd in cmds.items():
        print(f"\n=================== {name} ===================")
        stdin, stdout, stderr = client.exec_command(cmd)
        print(stdout.read().decode('utf-8', errors='replace'))
    
    client.close()

if __name__ == "__main__":
    run()
