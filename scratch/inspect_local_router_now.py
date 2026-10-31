import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("Connecting to local router 192.168.1.1:222...")
    client.connect('192.168.1.1', port=222, username='root', password='keenetic', timeout=10)

    commands = [
        "ps | grep -E 'router_api|ttyd|nfqws|lighttpd' | grep -v grep",
        "ls -la /opt/share/router-control-center",
        "cat /opt/etc/router-api.auth 2>/dev/null",
        "curl -s -I http://127.0.0.1:8089/ | head -n 5",
        "curl -s -X POST -H 'Content-Type: application/json' -d '{\"username\":\"admin\",\"password\":\"Salomanov\"}' http://127.0.0.1:8089/api/login",
        "curl -s -I http://127.0.0.1:90/ | head -n 5",
        "curl -s -X POST -d 'cmd=status' http://127.0.0.1:90/index.php",
        "netstat -tulnp | grep -E '8089|7681|7682|90'"
    ]

    for cmd in commands:
        print(f"\n=== CMD: {cmd} ===")
        stdin, stdout, stderr = client.exec_command(cmd)
        print(stdout.read().decode('utf-8', errors='replace').strip())

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
