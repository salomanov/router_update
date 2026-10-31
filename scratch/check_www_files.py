import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect('192.168.1.1', port=222, username='root', password='keenetic', timeout=10)

    commands = [
        "ls -la /opt/share/www",
        "ls -la /opt/share/www/nfqws",
        "cat /opt/etc/lighttpd/lighttpd.conf | grep -E 'server.document-root|server_root'"
    ]

    for cmd in commands:
        print(f"\n=== CMD: {cmd} ===")
        stdin, stdout, stderr = client.exec_command(cmd)
        print(stdout.read().decode('utf-8', errors='replace'))
except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
