#!/bin/sh

# ==================================================
# GRouter Control Panel Auto-Installer for Entware
# Authenticated management API + web dashboard
#
# No credentials are shipped with this script. The admin password is
# generated on the router at first start and printed once below.
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
DEPS="python3-light python3-openssl python3-email python3-logging python3-urllib python3-codecs python3-idna curl wget-ssl ca-certificates ca-bundle"
printf "Проверка зависимостей...\n"
opkg update > /dev/null 2>&1
opkg install $DEPS > /dev/null 2>&1

# Установка ttyd для веб-терминала PuTTY
printf "Установка Web-терминала ttyd (PuTTY в браузере)...\n"
opkg install --force-overwrite ttyd > /dev/null 2>&1 || true

# 3. Подготовка директорий
mkdir -p /opt/scripts /opt/etc/init.d /opt/etc/grouter /opt/share/router-control-center \
         /opt/share/www /opt/var/run /opt/var/log

# 4. Скачивание актуальных файлов с GitHub
REPO_RAW="https://raw.githubusercontent.com/salomanov/router_update/main"
CACHE_BUST="?nocache=$(date +%s)$$"

fetch() {
    # fetch <url> <destination>; fails loudly instead of leaving an empty file
    if ! curl -fsSL -o "$2" "$1"; then
        printf "${RED}Ошибка скачивания: %s${NC}\n" "$1"
        rm -f "$2"
        exit 1
    fi
    if [ ! -s "$2" ]; then
        printf "${RED}Скачанный файл пуст: %s${NC}\n" "$1"
        rm -f "$2"
        exit 1
    fi
}

printf "Скачивание бэкенда API и автозапуска...\n"
fetch "${REPO_RAW}/router_api.py${CACHE_BUST}" /opt/scripts/router_api.py
curl -fsSL -o /opt/scripts/opkg_update.py "${REPO_RAW}/opkg_update.py${CACHE_BUST}" 2>/dev/null \
    || printf "${YELLOW}Внимание: opkg_update.py не скачан, opkg update будет обычным.${NC}\n"
fetch "${REPO_RAW}/S90router-api${CACHE_BUST}" /opt/etc/init.d/S90router-api

printf "Скачивание веб-интерфейса GRouter...\n"
fetch "${REPO_RAW}/index.html${CACHE_BUST}" /opt/share/router-control-center/index.html
fetch "${REPO_RAW}/style.css${CACHE_BUST}" /opt/share/router-control-center/style.css
fetch "${REPO_RAW}/app.js${CACHE_BUST}" /opt/share/router-control-center/app.js

printf "Скачивание профиля пакетов и CLI...\n"
curl -fsSL -o /opt/etc/grouter/profile.json "${REPO_RAW}/configs/profile.json${CACHE_BUST}" 2>/dev/null \
    || printf "${YELLOW}Внимание: configs/profile.json не скачан — 'grouter plan' покажет пустой профиль.${NC}\n"
fetch "${REPO_RAW}/grouter_cli.py${CACHE_BUST}" /opt/scripts/grouter_cli.py

# Очищаем /opt/share/www от посторонних файлов, чтобы исключить конфликты с nfqws web на порту 90
rm -f /opt/share/www/index.html /opt/share/www/app.js /opt/share/www/style.css 2>/dev/null || true

# 5. ttyd: только loopback. Публичный порт 7681 обслуживает router_api.py,
# который проверяет сессию панели (иначе это был бы открытый root-shell).
TTYD_SHELL="/opt/bin/sh"
[ -x "$TTYD_SHELL" ] || TTYD_SHELL="/bin/sh"

cat << EOFTTYD > /opt/etc/init.d/S96ttyd
#!/bin/sh

ENABLED=yes
PROCS=ttyd
ARGS="-W -i 127.0.0.1 -p 7682 ${TTYD_SHELL}"
PREARGS=""
DESC="Web Terminal (ttyd, loopback only)"
PATH=/opt/sbin:/opt/bin:/opt/usr/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

. /opt/etc/init.d/rc.func
EOFTTYD
chmod +x /opt/etc/init.d/S96ttyd

# Старый скрипт с паролем в открытом виде больше не нужен
rm -f /opt/scripts/ttyd_shell.sh 2>/dev/null || true

# 5.1 Конфигурация lighttpd для nfqws-web (порт 90).
# Аутентификация nfqws-web НЕ отключается: это UI управления firewall/desync.
if [ -d "/opt/etc/lighttpd" ]; then
    mkdir -p /opt/etc/lighttpd/conf.d
    rm -f /opt/share/www/index.html /opt/share/www/app.js /opt/share/www/style.css 2>/dev/null || true
    cat << 'EOFLIGHT' > /opt/etc/lighttpd/conf.d/80-nfqws.conf
server.port := 90

cgi.assign += ( ".php" => "/opt/bin/php-cgi" )
static-file.exclude-extensions += ( ".php" )
setenv.set-environment = ( "PATH" => "/opt/sbin:/opt/bin:/opt/usr/sbin:/opt/usr/bin:/usr/sbin:/usr/bin:/sbin:/bin" )
index-file.names := ( "index.html" )
server.error-handler-404 = "/nfqws/index.html"
url.rewrite-once = ( "^/(.*)" => "/nfqws/$1" )
EOFLIGHT

    [ -x "/opt/etc/init.d/S80lighttpd" ] && /opt/etc/init.d/S80lighttpd restart > /dev/null 2>&1 || true
fi

# 6. CLI /opt/bin/grouter -> plan | apply | status | update-all
cat << 'EOFCLI' > /opt/bin/grouter
#!/bin/sh
exec /opt/bin/python3 /opt/scripts/grouter_cli.py "$@"
EOFCLI
chmod 755 /opt/bin/grouter

# 7. Права и запуск
chmod 755 /opt/scripts/router_api.py
chmod 755 /opt/scripts/grouter_cli.py
chmod 755 /opt/scripts/opkg_update.py 2>/dev/null || true
chmod 755 /opt/etc/init.d/S90router-api

# 7.1 Необязательные параметры пароля. Читаются только при ПЕРВОМ старте
# (иначе в /opt остался бы открытый пароль рядом с готовым хэшем).
if [ ! -f "/opt/etc/router-api.auth" ]; then
    if [ -n "$GROUTER_DEFAULT_PASSWORD" ]; then
        umask 077
        printf '%s\n' "$GROUTER_DEFAULT_PASSWORD" > /opt/etc/grouter/default_password
        umask 022
        printf "Задан свой пароль администратора (GROUTER_DEFAULT_PASSWORD).\n"
    fi
    if [ -n "$GROUTER_RANDOM_PASSWORD" ]; then
        : > /opt/etc/grouter/random_password
        printf "Включён режим одноразового случайного пароля.\n"
    fi
fi

printf "Запуск служб...\n"
/opt/etc/init.d/S96ttyd restart > /dev/null 2>&1 || true
/opt/etc/init.d/S90router-api restart

# 8. Пароль: стандартный сохраняется при первом старте, одноразовый — только в secure-режиме
sleep 2
INITIAL_PW_FILE="/opt/etc/grouter/initial_password"
LAN_IP=$(ip -4 addr show br0 2>/dev/null | grep -o 'inet [0-9.]*' | awk '{print $2}')
[ -z "$LAN_IP" ] && LAN_IP=$(ip -4 route get 1.1.1.1 2>/dev/null | grep -o 'src [0-9.]*' | awk '{print $2}')
[ -z "$LAN_IP" ] && LAN_IP="192.168.1.1"

printf "\n${GREEN}==========================================================${NC}\n"
printf "${GREEN}Установка GRouter завершена!${NC}\n"
printf "Панель управления: ${GREEN}http://%s:8089/${NC}\n" "$LAN_IP"
printf "Веб-терминал PuTTY: ${GREEN}http://%s:7681/${NC} (только после входа в панель)\n" "$LAN_IP"
printf "Логин: ${YELLOW}admin${NC}\n"

if [ -s "$INITIAL_PW_FILE" ]; then
    printf "Одноразовый пароль: ${YELLOW}%s${NC}\n" "$(cat "$INITIAL_PW_FILE")"
    printf "${YELLOW}Смените его при первом входе — до смены панель работает в ограниченном режиме.${NC}\n"
else
    printf "Пароль: ${YELLOW}Salomanov${NC} (стандартный, менять не обязательно)\n"
    printf "Сменить можно кнопкой с ключом в шапке панели.\n"
    printf "${YELLOW}Если пароль уже был изменён ранее и забыт: удалить${NC}\n"
    printf "${YELLOW}/opt/etc/router-api.auth и перезапустить S90router-api.${NC}\n"
fi

printf "\nПрофиль пакетов: ${GREEN}grouter plan${NC} (проверить) / ${GREEN}grouter apply${NC} (доставить)\n"
printf "${GREEN}==========================================================${NC}\n\n"
