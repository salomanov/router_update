import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect('178.140.8.56', port=34222, username='root', password='keenetic', timeout=10)

    cmd = "/opt/bin/python3 -c 'import hashlib; print(hasattr(hashlib, \"pbkdf2_hmac\")); print([x for x in dir(hashlib) if not x.startswith(\"_\")])'"
    stdin, stdout, stderr = client.exec_command(cmd)
    print("STDOUT:\n", stdout.read().decode('utf-8', errors='replace'))
    print("STDERR:\n", stderr.read().decode('utf-8', errors='replace'))

    cmd2 = "opkg list-installed | grep python3"
    stdin, stdout, stderr = client.exec_command(cmd2)
    print("Installed python packages:\n", stdout.read().decode('utf-8', errors='replace'))

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
