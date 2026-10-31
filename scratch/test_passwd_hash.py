import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect('192.168.1.1', port=222, username='root', password='keenetic', timeout=10)

    # Test PHP crypt with passwords 'keenetic' and 'Salomanov'
    cmd = """/opt/bin/php-cli -r '
$passwords = ["keenetic", "Salomanov", "admin", "root", "1234", "12345", "123456"];
$hash = "\$1\$6vKOV7zs\$d2EqNYGvlBWEYoFD7FFkr0";
foreach ($passwords as $p) {
    if (crypt($p, $hash) === $hash) {
        echo "MATCH FOUND: $p\n";
    }
}
' 2>/dev/null || /opt/bin/php-cgi -r '...' 2>/dev/null || echo "No php-cli" """

    stdin, stdout, stderr = client.exec_command(cmd)
    print(stdout.read().decode('utf-8', errors='replace'))
    print(stderr.read().decode('utf-8', errors='replace'))
except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
