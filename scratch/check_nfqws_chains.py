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

cmd = """
echo "=== 1. iptables mangle nfqws chains ==="
iptables -t mangle -L nfqws_pre -n -v
iptables -t mangle -L nfqws_post -n -v

echo "=== 2. Can router curl simulate client with desync? ==="
# Test with python curl or openssl s_client to instagram
openssl s_client -connect www.instagram.com:443 -servername www.instagram.com </dev/null 2>&1 | grep -iE 'handshake|cipher|verify|error|connected' || true
"""

stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='replace'))
client.close()
