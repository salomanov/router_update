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
echo "=== Test syntax for domain-specific upstream ==="
ndmc -c 'dns-proxy https upstream https://eu.geohide.ru/dns-query ?' 2>&1 || true
ndmc -c 'dns-proxy tls upstream eu.geohide.ru ?' 2>&1 || true
"""
stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='replace'))
client.close()
