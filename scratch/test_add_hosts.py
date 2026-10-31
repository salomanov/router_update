import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')

LOCAL_HOST = "192.168.1.1"
PORT = 222
USER = "root"
PASS = "keenetic"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(LOCAL_HOST, port=PORT, username=USER, password=PASS, timeout=5)

cmd = """
echo "104.21.28.172 crosspointreader.com www.crosspointreader.com" >> /etc/hosts
nslookup crosspointreader.com 127.0.0.1
"""
stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='replace'))

# remove it right after checking
client.exec_command("sed -i '/crosspointreader.com/d' /etc/hosts")
client.close()
