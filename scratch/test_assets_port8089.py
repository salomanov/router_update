import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect('192.168.1.1', port=222, username='root', password='keenetic', timeout=10)

    cmds = [
        "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8089/",
        "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8089/app.js",
        "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8089/style.css"
    ]

    for c in cmds:
        stdin, stdout, stderr = client.exec_command(c)
        print(f"{c} -> {stdout.read().decode('utf-8')}")

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
