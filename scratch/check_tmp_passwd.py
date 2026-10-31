import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect('192.168.1.1', port=222, username='root', password='keenetic', timeout=10)
    stdin, stdout, stderr = client.exec_command("cat /tmp/passwd 2>/dev/null; echo '---'; cat /etc/passwd 2>/dev/null")
    print(stdout.read().decode('utf-8', errors='replace'))
except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
