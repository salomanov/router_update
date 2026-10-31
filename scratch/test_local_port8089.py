import sys
import time
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect('192.168.1.1', port=222, username='root', password='keenetic', timeout=10)
    time.sleep(1)

    stdin, stdout, stderr = client.exec_command("ps | grep router_api; curl -s -I http://127.0.0.1:8089/")
    print(stdout.read().decode('utf-8', errors='replace'))

    stdin, stdout, stderr = client.exec_command("curl -s http://127.0.0.1:8089/ | head -n 15")
    print(stdout.read().decode('utf-8', errors='replace'))

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
