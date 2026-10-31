import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect('192.168.1.1', port=222, username='root', password='keenetic', timeout=10)
    print("SSH Connected!")

    commands = [
        "curl -s -X POST -d 'cmd=status' http://127.0.0.1:90/index.php",
        "curl -s -X POST -d 'cmd=filenames&type=conf' http://127.0.0.1:90/index.php",
        "curl -s -X POST -d 'cmd=filenames&type=list' http://127.0.0.1:90/index.php",
        "opkg status nfqws2-keenetic",
        "opkg status nfqws-keenetic",
        "which nfqws2; which nfqws; ls -la /opt/usr/bin/nfqws* 2>/dev/null",
        "ls -la /opt/etc/init.d/S*nfqws* 2>/dev/null",
        "cat /opt/share/www/nfqws/index.php | grep -n -C 5 'nfqwsInstalledVersion'"
    ]

    for cmd in commands:
        print(f"\n=== CMD: {cmd} ===")
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode('utf-8', errors='replace')
        print(out)
except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
