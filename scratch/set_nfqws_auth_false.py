import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect('192.168.1.1', port=222, username='root', password='keenetic', timeout=10)

    # Set auth.enabled = false in /opt/etc/nfqws_web.conf
    # Also add admin to /opt/etc/passwd if not present
    # And improve authenticate() in /opt/share/www/nfqws/index.php to accept admin / Salomanov / keenetic
    cmds = [
        "sed -i 's/enabled = true/enabled = false/' /opt/etc/nfqws_web.conf",
        "grep -q '^admin:' /opt/etc/passwd || echo 'admin:$1$6vKOV7zs$d2EqNYGvlBWEYoFD7FFkr0:0:0:Admin:/opt/root:/opt/bin/sh' >> /opt/etc/passwd",
        "cat /opt/etc/nfqws_web.conf"
    ]

    for cmd in cmds:
        print(f"=== {cmd} ===")
        stdin, stdout, stderr = client.exec_command(cmd)
        print(stdout.read().decode('utf-8', errors='replace'))
except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
