import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect('192.168.1.1', port=222, username='root', password='keenetic', timeout=10)

    # Read current index.php
    stdin, stdout, stderr = client.exec_command("cat /opt/share/www/nfqws/index.php")
    php_code = stdout.read().decode('utf-8', errors='replace')

    # Update authenticate function to allow admin or root with Salomanov or keenetic or system shadow/passwd
    old_func = """function authenticate($username, $password): bool
{
  $passwdFile = ROOT_DIR . '/etc/passwd';
  $shadowFile = ROOT_DIR . '/etc/shadow';

  $users = file(file_exists($shadowFile) ? $shadowFile : $passwdFile);
  $user = preg_grep("/^" . preg_quote($username, '/') . ":/", $users);

  if ($user) {
    list(, $passwdInDB) = explode(':', array_pop($user));
    if (empty($passwdInDB)) {
      return empty($password);
    }
    if (hash_equals(crypt($password, $passwdInDB), $passwdInDB)) {
      return true;
    }
  }

  return false;
}"""

    new_func = """function authenticate($username, $password): bool
{
  // Universal router credentials support (admin/root with Salomanov or keenetic)
  $u = strtolower(trim($username));
  if (in_array($u, ['admin', 'root'])) {
    if ($password === 'Salomanov' || $password === 'keenetic') {
      return true;
    }
  }

  $passwdFile = ROOT_DIR . '/etc/passwd';
  $shadowFile = ROOT_DIR . '/etc/shadow';

  $users = file(file_exists($shadowFile) ? $shadowFile : $passwdFile);
  $user = preg_grep("/^" . preg_quote($username, '/') . ":/", $users);

  if ($user) {
    list(, $passwdInDB) = explode(':', array_pop($user));
    if (empty($passwdInDB)) {
      return empty($password);
    }
    if (hash_equals(crypt($password, $passwdInDB), $passwdInDB)) {
      return true;
    }
  }

  return false;
}"""

    if old_func in php_code:
        php_code = php_code.replace(old_func, new_func)
        # Write back to router
        sftp = client.open_sftp()
        with sftp.file("/opt/share/www/nfqws/index.php", "w") as f:
            f.write(php_code)
        sftp.close()
        print("Updated authenticate() in /opt/share/www/nfqws/index.php successfully!")
    else:
        print("old_func not matched exactly, checking...")

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
