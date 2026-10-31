import sys
import time
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect('178.140.8.56', port=34222, username='root', password='keenetic', timeout=10)
    time.sleep(2)

    stdin, stdout, stderr = client.exec_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8089/")
    print("Remote 8089 HTTP code:", stdout.read().decode('utf-8').strip())

    stdin, stdout, stderr = client.exec_command("curl -s http://127.0.0.1:8089/ | head -n 5")
    print("Remote 8089 preview:\n", stdout.read().decode('utf-8').strip())

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
