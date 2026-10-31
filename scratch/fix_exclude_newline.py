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
# Fix accidental concatenation
sed -i 's/makerworld.comgoogle.com/makerworld.com\\ngoogle.com/g' /opt/etc/nfqws2/lists/exclude.list
# Ensure google.com is on its own line
grep -n 'google' /opt/etc/nfqws2/lists/exclude.list
/opt/etc/init.d/S51nfqws2 reload 2>/dev/null || /opt/etc/init.d/S51nfqws2 restart
"""
stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='replace'))
client.close()
