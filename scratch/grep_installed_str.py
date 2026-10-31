import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect('192.168.1.1', port=222, username='root', password='keenetic', timeout=10)

    # Grep in JS assets
    cmd = "grep -rn 'установ' /opt/share/www/nfqws/assets/ 2>/dev/null"
    stdin, stdout, stderr = client.exec_command(cmd)
    print("JS Grep output:\n", stdout.read().decode('utf-8', errors='replace'))

    # Check GRouter app.js or html
    cmd2 = "grep -rn 'установ' /opt/share/router-control-center/ 2>/dev/null"
    stdin, stdout, stderr = client.exec_command(cmd2)
    print("GRouter Grep output:\n", stdout.read().decode('utf-8', errors='replace'))

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
