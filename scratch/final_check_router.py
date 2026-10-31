import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect('178.140.8.56', port=34222, username='root', password='keenetic', timeout=10)

    cmds = [
        "ps | grep -E 'nfqws|lighttpd|router_api|ttyd'",
        "/opt/etc/init.d/S51nfqws2 status",
        "/opt/bin/php-cgi -l /opt/share/www/nfqws/index.php",
        "curl -s -X POST -d 'cmd=status' http://127.0.0.1:90/index.php"
    ]

    for cmd in cmds:
        print(f"\n=== {cmd} ===")
        stdin, stdout, stderr = client.exec_command(cmd)
        print(stdout.read().decode('utf-8', errors='replace').strip())

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
