import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect('178.140.8.56', port=34222, username='root', password='keenetic', timeout=10)

    commands = [
        "curl -s -X POST -d 'cmd=filenames&type=conf' http://127.0.0.1:90/index.php",
        "curl -s -X POST -d 'cmd=filenames&type=list' http://127.0.0.1:90/index.php",
        "curl -s -X POST -d 'cmd=filecontent&filename=nfqws2.conf' http://127.0.0.1:90/index.php | head -c 200",
        "curl -s -X POST -d 'cmd=filecontent&filename=user.list' http://127.0.0.1:90/index.php | head -c 200"
    ]

    for cmd in commands:
        print(f"\n=== CMD: {cmd} ===")
        stdin, stdout, stderr = client.exec_command(cmd)
        print(stdout.read().decode('utf-8', errors='replace'))

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
