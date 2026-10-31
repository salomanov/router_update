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

client.exec_command("sed -i '/crosspointreader/d' /etc/hosts")
client.close()
print("Cleaned up /etc/hosts on local router.")
