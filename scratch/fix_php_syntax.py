import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect('178.140.8.56', port=34222, username='root', password='keenetic', timeout=10)

    # Read current index.php
    stdin, stdout, stderr = client.exec_command("cat /opt/share/www/nfqws/index.php")
    php_code = stdout.read().decode('utf-8', errors='replace')

    # Remove the extra unclosed brace
    broken_block = """function authenticate($username, $password): bool
{
  $u = strtolower(trim($username));
  if (in_array($u, array("admin", "root"))) {
    if ($password === "Salomanov" || $password === "keenetic") { return true; }
  }
{"""

    fixed_block = """function authenticate($username, $password): bool
{
  $u = strtolower(trim($username));
  if (in_array($u, array("admin", "root"))) {
    if ($password === "Salomanov" || $password === "keenetic") { return true; }
  }"""

    if broken_block in php_code:
        php_code = php_code.replace(broken_block, fixed_block)
        print("Replaced broken block successfully!")
    else:
        # Also handle any variation with \r\n
        broken_block_crlf = broken_block.replace("\n", "\r\n")
        if broken_block_crlf in php_code:
            php_code = php_code.replace(broken_block_crlf, fixed_block)
            print("Replaced broken CRLF block successfully!")
        else:
            print("Block not found by exact string, doing regex/search...")
            import re
            php_code = re.sub(
                r'function authenticate\(\$username, \$password\): bool\s*\{\s*\$u = strtolower\(trim\(\$username\)\);.*?\}\s*\{',
                fixed_block,
                php_code,
                flags=re.DOTALL
            )

    # Write back via stdin
    stdin, stdout, stderr = client.exec_command("cat > /opt/share/www/nfqws/index.php")
    stdin.write(php_code)
    stdin.channel.shutdown_write()
    print("Write exit status:", stdout.channel.recv_exit_status())

    # Lint check
    stdin, stdout, stderr = client.exec_command("/opt/bin/php-cgi -l /opt/share/www/nfqws/index.php")
    print("PHP Lint result:\n", stdout.read().decode('utf-8', errors='replace'))

    # Status check via curl
    stdin, stdout, stderr = client.exec_command("curl -s -X POST -d 'cmd=status' http://127.0.0.1:90/index.php")
    print("API status response:\n", stdout.read().decode('utf-8', errors='replace'))

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
