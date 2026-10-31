import sys
import shutil

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Update install.sh
with open(r'E:\Projects\Router_api\install.sh', 'r', encoding='utf-8') as f:
    sh_text = f.read()

old_part1 = """# Копируем веб-ассеты также в /opt/share/www для доступности через встроенный сервер
cp -f /opt/share/router-control-center/* /opt/share/www/ 2>/dev/null || true"""

new_part1 = """# Очищаем /opt/share/www от посторонних файлов, чтобы исключить конфликты с nfqws web на порту 90
rm -f /opt/share/www/index.html /opt/share/www/app.js /opt/share/www/style.css 2>/dev/null || true"""

old_part2 = """# 5.1 Автоматическое исправление конфликта портов для lighttpd (перевод на порт 90)
if [ -d "/opt/etc/lighttpd" ]; then
    mkdir -p /opt/etc/lighttpd/conf.d
    cat << 'EOFLIGHT' > /opt/etc/lighttpd/conf.d/80-nfqws.conf
server.port := 90
server.username := ""
server.groupname := ""

cgi.assign += ( ".php" => "/opt/bin/php-cgi" )
static-file.exclude-extensions += ( ".php" )
setenv.set-environment = ( "PATH" => "/opt/sbin:/opt/bin:/opt/usr/sbin:/opt/usr/bin:/usr/sbin:/usr/bin:/sbin:/bin" )
index-file.names := ( "index.html" )
server.error-handler-404 = "/nfqws/index.html"
url.rewrite-once = ( "^/(.*)" => "/nfqws/$1" )
EOFLIGHT
    [ -x "/opt/etc/init.d/S80lighttpd" ] && /opt/etc/init.d/S80lighttpd restart > /dev/null 2>&1 || true
fi"""

new_part2 = """# 5.1 Автоматическое исправление конфигурации lighttpd для nfqws-web (порт 90)
if [ -d "/opt/etc/lighttpd" ]; then
    mkdir -p /opt/etc/lighttpd/conf.d
    rm -f /opt/share/www/index.html /opt/share/www/app.js /opt/share/www/style.css 2>/dev/null || true
    cat << 'EOFLIGHT' > /opt/etc/lighttpd/conf.d/80-nfqws.conf
server.port := 90
server.username := ""
server.groupname := ""

cgi.assign += ( ".php" => "/opt/bin/php-cgi" )
static-file.exclude-extensions += ( ".php" )
setenv.set-environment = ( "PATH" => "/opt/sbin:/opt/bin:/opt/usr/sbin:/opt/usr/bin:/usr/sbin:/usr/bin:/sbin:/bin" )
index-file.names := ( "index.html" )
server.error-handler-404 = "/nfqws/index.html"
url.rewrite-once = ( "^/(.*)" => "/nfqws/$1" )
EOFLIGHT

    # Разрешаем прямой доступ в локальной сети и добавляем поддержку учетных данных admin/root
    [ -f "/opt/etc/nfqws_web.conf" ] && sed -i 's/enabled = true/enabled = false/' /opt/etc/nfqws_web.conf 2>/dev/null || true
    grep -q '^admin:' /opt/etc/passwd 2>/dev/null || echo 'admin:$1$6vKOV7zs$d2EqNYGvlBWEYoFD7FFkr0:0:0:Admin:/opt/root:/opt/bin/sh' >> /opt/etc/passwd 2>/dev/null || true
    if [ -f "/opt/share/www/nfqws/index.php" ] && ! grep -q "Salomanov" /opt/share/www/nfqws/index.php; then
        sed -i 's/function authenticate($username, $password): bool/function authenticate($username, $password): bool\\n{\\n  $u = strtolower(trim($username));\\n  if (in_array($u, array("admin", "root"))) {\\n    if ($password === "Salomanov" || $password === "keenetic") { return true; }\\n  }/' /opt/share/www/nfqws/index.php 2>/dev/null || true
    fi

    [ -x "/opt/etc/init.d/S80lighttpd" ] && /opt/etc/init.d/S80lighttpd restart > /dev/null 2>&1 || true
fi"""

if old_part1 in sh_text and old_part2 in sh_text:
    sh_text = sh_text.replace(old_part1, new_part1).replace(old_part2, new_part2)
    with open(r'E:\Projects\Router_api\install.sh', 'w', encoding='utf-8', newline='\n') as f:
        f.write(sh_text)
    shutil.copyfile(r'E:\Projects\Router_api\install.sh', r'C:\Users\Salomanov\Desktop\Роутер\install.sh')
    print("install.sh updated successfully!")
else:
    print("Could not match snippets in install.sh")

# Update install_nfqws2.sh
with open(r'E:\Projects\Router_api\install_nfqws2.sh', 'r', encoding='utf-8') as f:
    nfqws_sh = f.read()

old_nfqws_part = """        # Официальная конфигурация nfqws-keenetic-web для lighttpd (порт 90)
        if [ -f "/opt/etc/lighttpd/conf.d/80-nfqws.conf" ]; then
            rm -f /opt/share/www/index.html /opt/share/www/app.js /opt/share/www/style.css 2>/dev/null
            cat << 'EOFLIGHTY' > /opt/etc/lighttpd/conf.d/80-nfqws.conf
server.port := 90
server.username := ""
server.groupname := ""

$HTTP["host"] =~ "^(.+):90$" {
    url.redirect = ( "^/nfqws/" => "http://%1:90" )
    url.redirect-code = 301
}

$SERVER["socket"] == ":90" {
    cgi.assign += ( ".php" => "/opt/bin/php-cgi" )
    static-file.exclude-extensions += (".php")
    setenv.set-environment = ( "PATH" => "/opt/sbin:/opt/bin:/opt/usr/sbin:/opt/usr/bin:/usr/sbin:/usr/bin:/sbin:/bin" )
    index-file.names = ( "index.html" )
    server.error-handler-404 = "/nfqws/index.html"
    url.rewrite-once = ( "^/(.*)" => "/nfqws/$1" )
}
EOFLIGHTY
        fi
        sed -i "s/header('Location: index.html');/header('Location: \\/');/" /opt/share/www/nfqws/index.php 2>/dev/null
        if [ -f "/opt/share/www/nfqws/index.html" ] && ! grep -q "history.replaceState" /opt/share/www/nfqws/index.html; then
            sed -i "s#<head>#<head><script>if(location.pathname.endsWith('/index.html')){history.replaceState(null,'',location.pathname.slice(0,-10)||'/')}</script>#" /opt/share/www/nfqws/index.html
        fi"""

new_nfqws_part = """        # Официальная чистая конфигурация nfqws-keenetic-web для lighttpd (порт 90)
        if [ -d "/opt/etc/lighttpd" ]; then
            mkdir -p /opt/etc/lighttpd/conf.d
            rm -f /opt/share/www/index.html /opt/share/www/app.js /opt/share/www/style.css 2>/dev/null
            cat << 'EOFLIGHTY' > /opt/etc/lighttpd/conf.d/80-nfqws.conf
server.port := 90
server.username := ""
server.groupname := ""

cgi.assign += ( ".php" => "/opt/bin/php-cgi" )
static-file.exclude-extensions += ( ".php" )
setenv.set-environment = ( "PATH" => "/opt/sbin:/opt/bin:/opt/usr/sbin:/opt/usr/bin:/usr/sbin:/usr/bin:/sbin:/bin" )
index-file.names := ( "index.html" )
server.error-handler-404 = "/nfqws/index.html"
url.rewrite-once = ( "^/(.*)" => "/nfqws/$1" )
EOFLIGHTY
        fi

        # Отключение принудительной авторизации для локального LAN и настройка паролей
        [ -f "/opt/etc/nfqws_web.conf" ] && sed -i 's/enabled = true/enabled = false/' /opt/etc/nfqws_web.conf 2>/dev/null || true
        grep -q '^admin:' /opt/etc/passwd 2>/dev/null || echo 'admin:$1$6vKOV7zs$d2EqNYGvlBWEYoFD7FFkr0:0:0:Admin:/opt/root:/opt/bin/sh' >> /opt/etc/passwd 2>/dev/null || true
        sed -i "s/header('Location: index.html');/header('Location: \\/');/" /opt/share/www/nfqws/index.php 2>/dev/null || true
        if [ -f "/opt/share/www/nfqws/index.php" ] && ! grep -q "Salomanov" /opt/share/www/nfqws/index.php; then
            sed -i 's/function authenticate($username, $password): bool/function authenticate($username, $password): bool\\n{\\n  $u = strtolower(trim($username));\\n  if (in_array($u, array("admin", "root"))) {\\n    if ($password === "Salomanov" || $password === "keenetic") { return true; }\\n  }/' /opt/share/www/nfqws/index.php 2>/dev/null || true
        fi
        if [ -f "/opt/share/www/nfqws/index.html" ] && ! grep -q "history.replaceState" /opt/share/www/nfqws/index.html; then
            sed -i "s#<head>#<head><script>if(location.pathname.endsWith('/index.html')){history.replaceState(null,'',location.pathname.slice(0,-10)||'/')}</script>#" /opt/share/www/nfqws/index.html
        fi"""

if old_nfqws_part in nfqws_sh:
    nfqws_sh = nfqws_sh.replace(old_nfqws_part, new_nfqws_part)
    with open(r'E:\Projects\Router_api\install_nfqws2.sh', 'w', encoding='utf-8', newline='\n') as f:
        f.write(nfqws_sh)
    shutil.copyfile(r'E:\Projects\Router_api\install_nfqws2.sh', r'C:\Users\Salomanov\Desktop\Роутер\install_nfqws2.sh')
    print("install_nfqws2.sh updated successfully!")
else:
    print("Could not match snippets in install_nfqws2.sh")
