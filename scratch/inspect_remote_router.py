import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("Connecting to 178.140.8.56:34222...")
    # Try root:keenetic and root:Salomanov
    try:
        client.connect('178.140.8.56', port=34222, username='root', password='keenetic', timeout=10)
        print("Connected with password: keenetic")
    except Exception as e:
        print(f"Failed with keenetic: {e}. Trying Salomanov...")
        client.connect('178.140.8.56', port=34222, username='root', password='Salomanov', timeout=10)
        print("Connected with password: Salomanov")

    cmds = [
        "uname -a",
        "ip addr show",
        "cat /opt/etc/lighttpd/conf.d/80-nfqws.conf 2>/dev/null",
        "cat /opt/etc/nfqws_web.conf 2>/dev/null",
        "opkg list-installed | grep -E 'nfqws|lighttpd'",
        "curl -s -X POST -d 'cmd=status' http://127.0.0.1:90/index.php 2>/dev/null",
        "ps | grep -E 'nfqws|lighttpd'"
    ]

    for cmd in cmds:
        print(f"\n=== CMD: {cmd} ===")
        stdin, stdout, stderr = client.exec_command(cmd)
        print(stdout.read().decode('utf-8', errors='replace'))

except Exception as e:
    print(f"SSH Error: {e}")
finally:
    client.close()
