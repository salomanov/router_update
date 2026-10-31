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
        "cat /opt/etc/lighttpd/conf.d/80-nfqws.conf",
        "cat /opt/etc/nfqws_web.conf 2>/dev/null || echo 'no /opt/etc/nfqws_web.conf'",
        "curl -s -i -X POST -d 'cmd=status' http://127.0.0.1:90/index.php",
        "curl -s -i -X POST -d 'cmd=status' http://127.0.0.1:90/nfqws/index.php",
        "tail -n 25 /opt/var/log/lighttpd/error.log"
    ]

    for cmd in commands:
        print(f"\n=== CMD: {cmd} ===")
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode('utf-8', errors='replace')
        err = stderr.read().decode('utf-8', errors='replace')
        if out:
            print(f"STDOUT:\n{out}")
        if err:
            print(f"STDERR:\n{err}")

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
