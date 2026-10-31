import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("Connecting to remote router 178.140.8.56:34222...")
    client.connect('178.140.8.56', port=34222, username='root', password='keenetic', timeout=10)
    print("Connected successfully!")

    commands = [
        "ls -lt /tmp | head -n 15",
        "ls -lt /opt/var/log | head -n 10",
        "cat /opt/var/log/router-api.log 2>/dev/null || echo 'no router-api.log'",
        "ps | grep -E 'router_api|ttyd|lighttpd'",
        "cat /opt/var/run/router-api.pid 2>/dev/null || echo 'no pid'",
        "curl -s -i http://127.0.0.1:8089/ 2>/dev/null | head -n 10",
        "cat /opt/etc/init.d/S90router-api status 2>/dev/null || /opt/etc/init.d/S90router-api status"
    ]

    for cmd in commands:
        print(f"\n=== CMD: {cmd} ===")
        stdin, stdout, stderr = client.exec_command(cmd)
        print(stdout.read().decode('utf-8', errors='replace').strip())

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
