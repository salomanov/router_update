import paramiko
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

HOST = "178.140.8.56"
PORT = 34222
USER = "root"
PASS = "keenetic"

def run_php_batch_check():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
    
    php_code = """<?php
require_once '/opt/share/www/nfqws/index.php';
$domains = [
    'youtube.com',
    'googlevideo.com',
    'i.ytimg.com',
    'discord.com',
    'discordapp.com',
    'instagram.com',
    'facebook.com',
    'rutracker.org',
    'bt.t-ru.org',
    'ya.ru',
    'vk.com'
];
$res = [];
foreach ($domains as $d) {
    $ok = checkResponseBodyReadable("https://$d", 10);
    $res[$d] = $ok ? 'OK (Доступен)' : 'FAIL (Заблокирован)';
}
echo json_encode($res, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE) . PHP_EOL;
"""
    
    stdin, stdout, stderr = client.exec_command("cat > /tmp/test_check.php")
    stdin.write(php_code)
    stdin.channel.shutdown_write()
    stdout.read()

    stdin, stdout, stderr = client.exec_command("php-cli /tmp/test_check.php", timeout=60)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print("PHP CHECK RESULT:")
    print(out)
    if err.strip():
        print("STDERR:", err)
    
    client.exec_command("rm -f /tmp/test_check.php")
    client.close()

if __name__ == "__main__":
    run_php_batch_check()
