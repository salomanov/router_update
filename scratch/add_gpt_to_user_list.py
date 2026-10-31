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
# Add OpenAI and ChatGPT domains to user.list
for d in chatgpt.com openai.com oaistatic.com oaiusercontent.com; do
    grep -q "^$d$" /opt/etc/nfqws2/lists/user.list || echo "$d" >> /opt/etc/nfqws2/lists/user.list
done

/opt/etc/init.d/S51nfqws2 restart
sleep 2

echo "=== Test curl ChatGPT with nfqws2 desync ==="
curl -svo /dev/null --connect-timeout 5 https://chatgpt.com 2>&1 | head -n 30
"""
stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='replace'))
client.close()
