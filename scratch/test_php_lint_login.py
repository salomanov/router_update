import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect('192.168.1.1', port=222, username='root', password='keenetic', timeout=10)

    stdin, stdout, stderr = client.exec_command("/opt/bin/php-cgi -l /opt/share/www/nfqws/index.php")
    print("Lint output:", stdout.read().decode('utf-8', errors='replace'))

    # Test login with admin:Salomanov via curl
    stdin, stdout, stderr = client.exec_command("curl -s -i -X POST -d 'cmd=login&user=admin&password=Salomanov' http://127.0.0.1:90/index.php")
    print("Login admin:Salomanov response:\n", stdout.read().decode('utf-8', errors='replace'))

    # Test login with root:keenetic via curl
    stdin, stdout, stderr = client.exec_command("curl -s -i -X POST -d 'cmd=login&user=root&password=keenetic' http://127.0.0.1:90/index.php")
    print("Login root:keenetic response:\n", stdout.read().decode('utf-8', errors='replace'))

    # Test status without auth (since auth.enabled = false)
    stdin, stdout, stderr = client.exec_command("curl -s -i -X POST -d 'cmd=status' http://127.0.0.1:90/index.php")
    print("Status response (auth.enabled = false):\n", stdout.read().decode('utf-8', errors='replace'))

finally:
    client.close()
