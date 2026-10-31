import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect('192.168.1.1', port=222, username='root', password='keenetic', timeout=10)

    commands = [
        "/opt/etc/init.d/S51nfqws2 status",
        "ps | grep -E 'nfqws|lighttpd|router_api|ttyd'",
        "cat /opt/var/log/nfqws2.log 2>/dev/null || echo 'no nfqws2.log'",
        "cat /opt/etc/nfqws2/nfqws2.conf | head -n 30"
    ]

    for cmd in commands:
        print(f"\n=== CMD: {cmd} ===")
        stdin, stdout, stderr = client.exec_command(cmd)
        print(stdout.read().decode('utf-8', errors='replace'))
except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
