import paramiko
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

HOST = "178.140.8.56"
PORT = 34222
USER = "root"
PASS = "keenetic"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=12)

cmd = """
ps | grep ndnproxy
echo "=== nslookup chatgpt.com ==="
nslookup chatgpt.com 127.0.0.1
echo "=== nslookup google.com ==="
nslookup google.com 127.0.0.1
"""
stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='replace'))
client.close()
