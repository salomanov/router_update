import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect('178.140.8.56', port=34222, username='root', password='keenetic', timeout=10)

    cmd = "/opt/bin/python3 -c 'import hashlib; print(hasattr(hashlib, \"pbkdf2_hmac\"))'"
    stdin, stdout, stderr = client.exec_command(cmd)
    print("STDOUT:", stdout.read().decode('utf-8', errors='replace').strip())

    cmd2 = "/opt/etc/init.d/S90router-api restart"
    stdin, stdout, stderr = client.exec_command(cmd2)
    print("Restart output:\n", stdout.read().decode('utf-8', errors='replace').strip())

    cmd3 = "sleep 1; curl -s -I http://127.0.0.1:8089/ | head -n 5"
    stdin, stdout, stderr = client.exec_command(cmd3)
    print("Port 8089 HEAD output:\n", stdout.read().decode('utf-8', errors='replace').strip())

    cmd4 = "curl -s -X POST -H 'Content-Type: application/json' -d '{\"username\":\"admin\",\"password\":\"Salomanov\"}' http://127.0.0.1:8089/api/login"
    stdin, stdout, stderr = client.exec_command(cmd4)
    print("Login output:\n", stdout.read().decode('utf-8', errors='replace').strip())

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
