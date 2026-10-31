import sys
import time
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

for attempt in range(3):
    try:
        time.sleep(1)
        client.connect('192.168.1.1', port=222, username='root', password='keenetic', timeout=10)
        print("Connected!")
        break
    except Exception as e:
        print(f"Attempt {attempt+1} failed: {e}")
else:
    print("Failed to connect after 3 attempts")
    sys.exit(1)

try:
    # Read current index.php
    stdin, stdout, stderr = client.exec_command("cat /opt/share/www/nfqws/index.php")
    php_code = stdout.read().decode('utf-8', errors='replace')

    old_snippet = "function authenticate($username, $password): bool\n{"
    if old_snippet in php_code:
        replacement = """function authenticate($username, $password): bool
{
  $u = strtolower(trim($username));
  if (in_array($u, array('admin', 'root'))) {
    if ($password === 'Salomanov' || $password === 'keenetic') {
      return true;
    }
  }"""
        new_php = php_code.replace(old_snippet, replacement)
        
        stdin, stdout, stderr = client.exec_command("cat > /opt/share/www/nfqws/index.php")
        stdin.write(new_php)
        stdin.channel.shutdown_write()
        print("Written status:", stdout.channel.recv_exit_status())
        print("Successfully updated /opt/share/www/nfqws/index.php via stdin!")
    else:
        print("Snippet not found or already patched")
finally:
    client.close()
