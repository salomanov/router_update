import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect('192.168.1.1', port=222, username='root', password='keenetic', timeout=10)

    cmd = "/opt/bin/python3 -c 'import hashlib; print(hasattr(hashlib, \"pbkdf2_hmac\"))'"
    stdin, stdout, stderr = client.exec_command(cmd)
    print("Local router hasattr pbkdf2_hmac:\n", stdout.read().decode('utf-8', errors='replace'))

    cmd2 = "opkg list-installed | grep python3-openssl"
    stdin, stdout, stderr = client.exec_command(cmd2)
    print("Local router python3-openssl:\n", stdout.read().decode('utf-8', errors='replace'))

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
