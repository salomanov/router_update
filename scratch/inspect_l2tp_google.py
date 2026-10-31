import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')

HOST = "178.140.8.56"
PORT = 34222
USER = "root"
PASS = "keenetic"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=12)

cmds = {
    "1. L2TP Netfilter hook check": "cat /opt/etc/ndm/netfilter.d/015-l2tp.sh 2>/dev/null || echo 'NOT FOUND'",
    "2. Check iptables mangle FORWARD": "iptables -t mangle -L FORWARD -n -v",
    "3. Check iptables filter FORWARD": "iptables -L FORWARD -n -v",
    "4. Check iptables nat POSTROUTING": "iptables -t nat -L POSTROUTING -n -v",
    "5. Check iptables mangle POSTROUTING": "iptables -t mangle -L POSTROUTING -n -v",
    "6. Check conntrack for 172.16.2.33": "grep '172.16.2.33' /proc/net/nf_conntrack",
    "7. Check what is listening on 8480": "netstat -tulpn | grep 8480 || true",
    "8. Check nfqws2 rules for l2tp": "iptables -t mangle -L nfqws_post -n -v; iptables -t mangle -L nfqws_pre -n -v"
}

for title, cmd in cmds.items():
    print(f"\n=================== {title} ===================")
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out.strip():
        print(out.strip())
    if err.strip():
        print(f"[ERR]: {err.strip()}")

client.close()
