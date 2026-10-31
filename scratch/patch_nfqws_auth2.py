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
        # Let's insert the fallback right at the top of authenticate()
        replacement = """function authenticate($username, $password): bool
{
  $u = strtolower(trim($username));
  if (in_array($u, ['admin', 'root'])) {
    if ($password === 'Salomanov' || $password === 'keenetic') {
      return true;
    }
  }"""
        new_php = php_code.replace(old_snippet, replacement)
        sftp = client.open_sftp()
        with sftp.file("/opt/share/www/nfqws/index.php", "w") as f:
            f.write(new_php)
        sftp.close()
        print("Updated /opt/share/www/nfqws/index.php successfully!")
    else:
        print("Snippet not found")
finally:
    client.close()
