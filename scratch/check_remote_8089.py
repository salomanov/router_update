import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("Checking REMOTE router 178.140.8.56:34222...")
    client.connect('178.140.8.56', port=34222, username='root', password='keenetic', timeout=10)

    cmds = [
        "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8089/ 2>/dev/null || echo 'fail'",
        "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:90/ 2>/dev/null || echo 'fail'",
        "ls -la /opt/share/router-control-center 2>/dev/null || echo 'no rcc'",
        "cat /opt/scripts/router_api.py | grep 'search_paths' -A 5 2>/dev/null || echo 'no grep'"
    ]

    for c in cmds:
        stdin, stdout, stderr = client.exec_command(c)
        print(f"{c} -> {stdout.read().decode('utf-8').strip()}")

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
