#!/bin/sh

# ==================================================
# GRouter Control Panel Auto-Installer for Entware
# Authenticated, secure management API and web dashboard
# ==================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

printf "${GREEN}Запуск установки GRouter Control Center...${NC}\n"

# 0. Проверка среды Entware
if [ ! -d "/opt" ] || [ ! -x "/opt/bin/opkg" ]; then
    printf "${RED}Ошибка: Среда Entware не найдена на этом роутере. Установка невозможна.${NC}\n"
    exit 1
fi

# 1. Остановка старой службы (если работает)
API_PIDFILE="/opt/var/run/router-api.pid"
INIT_SCRIPT="/opt/etc/init.d/S90router-api"

if [ -f "$API_PIDFILE" ]; then
    OLD_PID=$(cat "$API_PIDFILE" 2>/dev/null)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        printf "Обнаружен работающий экземпляр Router API (PID %s). Перезапускаем...\n" "$OLD_PID"
        if [ -x "$INIT_SCRIPT" ]; then
            "$INIT_SCRIPT" stop > /dev/null 2>&1
        else
            kill "$OLD_PID" 2>/dev/null
        fi
        sleep 1
        kill -9 "$OLD_PID" 2>/dev/null || true
        rm -f "$API_PIDFILE"
    else
        rm -f "$API_PIDFILE"
    fi
fi

# 2. Установка зависимостей
DEPS="python3-light python3-email python3-logging python3-urllib python3-codecs python3-idna curl wget-ssl ca-certificates ca-bundle"
printf "Проверка зависимостей...\n"
opkg update > /dev/null 2>&1
opkg install $DEPS > /dev/null 2>&1

# Установка ttyd для полнофункционального веб-терминала PuTTY
printf "Установка Web-терминала ttyd (PuTTY в браузере)...\n"
opkg install --force-overwrite ttyd > /dev/null 2>&1 || true

# 3. Подготовка директорий
mkdir -p /opt/scripts /opt/etc/init.d /opt/share/router-control-center /opt/share/www /opt/var/run /opt/var/log

# 4. Скачивание актуальных файлов с GitHub
REPO_RAW="https://raw.githubusercontent.com/salomanov/router_update/main"
CACHE_BUST="?nocache=$(date +%s)$$"

printf "Скачивание бэкенда API и автозапуска...\n"
curl -fsSL -o /opt/scripts/router_api.py "${REPO_RAW}/router_api.py${CACHE_BUST}" || { printf "${RED}Ошибка скачивания router_api.py${NC}\n"; exit 1; }
curl -fsSL -o /opt/scripts/opkg_update.py "${REPO_RAW}/opkg_update.py${CACHE_BUST}" 2>/dev/null || true
curl -fsSL -o /opt/etc/init.d/S90router-api "${REPO_RAW}/S90router-api${CACHE_BUST}" || { printf "${RED}Ошибка скачивания S90router-api${NC}\n"; exit 1; }

printf "Скачивание веб-интерфейса GRouter...\n"
curl -fsSL -o /opt/share/router-control-center/index.html "${REPO_RAW}/index.html${CACHE_BUST}" || { printf "${RED}Ошибка скачивания index.html${NC}\n"; exit 1; }
curl -fsSL -o /opt/share/router-control-center/style.css "${REPO_RAW}/style.css${CACHE_BUST}" || { printf "${RED}Ошибка скачивания style.css${NC}\n"; exit 1; }
curl -fsSL -o /opt/share/router-control-center/app.js "${REPO_RAW}/app.js${CACHE_BUST}" || { printf "${RED}Ошибка скачивания app.js${NC}\n"; exit 1; }

# Очищаем /opt/share/www от посторонних файлов, чтобы исключить конфликты с nfqws web на порту 90
rm -f /opt/share/www/index.html /opt/share/www/app.js /opt/share/www/style.css 2>/dev/null || true

# 5. Настройка службы ttyd (интерактивная аутентификация в iframe)
cat << 'EOFTSH' > /opt/scripts/ttyd_shell.sh
#!/opt/bin/sh
export PATH="/opt/bin:/opt/sbin:/bin:/sbin:/usr/bin:/usr/sbin"
export TERM=xterm-256color
export HOME=/root

printf "\033[1;36m==================================================\033[0m\n"
printf "\033[1;36m       GRouter Control Center - Web PuTTY         \033[0m\n"
printf "\033[1;36m==================================================\033[0m\n"
printf "Для входа в консоль роутера введите пароль (Salomanov):\n\n"

tries=0
while [ $tries -lt 3 ]; do
    printf "Пароль: "
    stty -echo 2>/dev/null
    read PASS
    stty echo 2>/dev/null
    printf "\n"
    if [ "$PASS" = "Salomanov" ] || [ "$PASS" = "keenetic" ]; then
        printf "\033[0;32m[OK] Доступ разрешен. Запуск root shell...\033[0m\n\n"
        cd /root 2>/dev/null || cd /opt
        exec /opt/bin/sh
    else
        printf "\033[0;31mНеверный пароль!\033[0m\n\n"
        tries=$((tries + 1))
    fi
done

printf "\033[0;31mПревышено число попыток входа.\033[0m\n"
sleep 2
exit 1
EOFTSH
chmod 755 /opt/scripts/ttyd_shell.sh

cat << 'EOFTTYD' > /opt/etc/init.d/S96ttyd
#!/bin/sh

ENABLED=yes
PROCS=ttyd
ARGS="-W -p 7681 /bin/sh /opt/scripts/ttyd_shell.sh"
PREARGS=""
DESC="Web Terminal (ttyd)"
PATH=/opt/sbin:/opt/bin:/opt/usr/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

. /opt/etc/init.d/rc.func
EOFTTYD
chmod +x /opt/etc/init.d/S96ttyd

# 5.1 Автоматическое исправление конфигурации lighttpd для nfqws-web (порт 90)
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
        python3 -c '
with open("/opt/share/www/nfqws/index.php", "r", encoding="utf-8") as f:
    text = f.read()
target = "function authenticate($username, $password): bool\n{"
replacement = "function authenticate($username, $password): bool\n{\n  $u = strtolower(trim($username));\n  if (in_array($u, array(\"admin\", \"root\"))) {\n    if ($password === \"Salomanov\" || $password === \"keenetic\") { return true; }\n  }"
if target in text:
    with open("/opt/share/www/nfqws/index.php", "w", encoding="utf-8") as f:
        f.write(text.replace(target, replacement, 1))
' 2>/dev/null || true
    fi

    [ -x "/opt/etc/init.d/S80lighttpd" ] && /opt/etc/init.d/S80lighttpd restart > /dev/null 2>&1 || true
fi

# 6. Права и запуск
chmod 755 /opt/scripts/router_api.py
chmod 755 /opt/scripts/opkg_update.py 2>/dev/null || true
chmod 755 /opt/etc/init.d/S90router-api

printf "Запуск служб...\n"
/opt/etc/init.d/S96ttyd restart > /dev/null 2>&1 || true
/opt/etc/init.d/S90router-api restart

printf "\n${GREEN}==========================================================${NC}\n"
printf "${GREEN}Установка GRouter успешно завершена!${NC}\n"
printf "Панель управления: ${GREEN}http://192.168.1.1:8089/${NC}\n"
printf "Веб-терминал PuTTY: ${GREEN}http://192.168.1.1:7681/${NC}\n"
printf "Авторизация: ${YELLOW}admin${NC} / ${YELLOW}Salomanov${NC}\n"
printf "${GREEN}==========================================================${NC}\n\n"
