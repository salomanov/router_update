#!/bin/sh

# ==========================================================
# Module 07: GRouter Dashboard (Port 8089) & Web Terminal (Port 7681)
# ==========================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

printf "${GREEN}=== Установка GRouter Панели и Web-терминала PuTTY ===${NC}\n"

if [ "$(id -u)" != "0" ]; then
    printf "${RED}Ошибка: Скрипт должен быть запущен с правами root.${NC}\n"
    exit 1
fi

if [ ! -d "/opt" ] || [ ! -x "/opt/bin/opkg" ]; then
    printf "${RED}Ошибка: Среда Entware (/opt) не найдена на этом роутере.${NC}\n"
    exit 1
fi

export PATH="/opt/bin:/opt/sbin:/bin:/sbin:/usr/bin:/usr/sbin"

# 1. Остановка старых процессов (включая старые версии gpanel без pidfile)
if [ -f "/opt/var/run/router-api.pid" ]; then
    OLD_PID=$(cat "/opt/var/run/router-api.pid" 2>/dev/null)
    [ -n "$OLD_PID" ] && kill "$OLD_PID" 2>/dev/null || true
    rm -f "/opt/var/run/router-api.pid"
fi
for spid in $(pgrep -f "router_api\.py" 2>/dev/null); do
    kill "$spid" 2>/dev/null || true
done
sleep 1

# 2. Установка зависимостей (полный python3 включает subprocess и весь stdlib)
DEPS="python3 python3-openssl curl ca-certificates"
printf "${YELLOW}Проверка зависимостей...${NC}\n"
if [ -x "/opt/scripts/opkg_update.py" ]; then
    python3 /opt/scripts/opkg_update.py >/dev/null 2>&1 || opkg update >/dev/null 2>&1
else
    opkg update >/dev/null 2>&1
fi
opkg install $DEPS >/dev/null 2>&1
# Выравниваем базовые пакеты python3 при обновлении со старого Entware (например, 3.13 -> 3.14)
opkg upgrade libpython3 python3-base python3-light python3-codecs python3-email python3-logging python3-urllib python3-openssl >/dev/null 2>&1 || true
opkg install --force-overwrite ttyd >/dev/null 2>&1 || true

# 3. Подготовка директорий
mkdir -p /opt/scripts /opt/scripts/modules /opt/etc/init.d /opt/etc/grouter \
         /opt/share/router-control-center /opt/var/run /opt/var/log /opt/tmp /opt/bin

REPO_RAW="https://raw.githubusercontent.com/salomanov/router_update/main"
CACHE_BUST="?nocache=$(date +%s)$$"

fetch() {
    curl -fsSL --max-time 30 -o "$2" "$1" 2>/dev/null || true
    if [ ! -s "$2" ]; then
        printf "${RED}Ошибка скачивания: %s${NC}\n" "$1"
        rm -f "$2"
        return 1
    fi
    chmod 755 "$2"
    return 0
}

# 4. Скачивание ядра и интерфейса
printf "${YELLOW}Загрузка бэкенда и веб-интерфейса...${NC}\n"
fetch "${REPO_RAW}/core/api.py${CACHE_BUST}" /opt/scripts/router_api.py || fetch "${REPO_RAW}/router_api.py${CACHE_BUST}" /opt/scripts/router_api.py
fetch "${REPO_RAW}/core/opkg_update.py${CACHE_BUST}" /opt/scripts/opkg_update.py 2>/dev/null || true
fetch "${REPO_RAW}/core/S90router-api${CACHE_BUST}" /opt/etc/init.d/S90router-api || fetch "${REPO_RAW}/S90router-api${CACHE_BUST}" /opt/etc/init.d/S90router-api

fetch "${REPO_RAW}/web/index.html${CACHE_BUST}" /opt/share/router-control-center/index.html || fetch "${REPO_RAW}/index.html${CACHE_BUST}" /opt/share/router-control-center/index.html
fetch "${REPO_RAW}/web/style.css${CACHE_BUST}" /opt/share/router-control-center/style.css || fetch "${REPO_RAW}/style.css${CACHE_BUST}" /opt/share/router-control-center/style.css
fetch "${REPO_RAW}/web/app.js${CACHE_BUST}" /opt/share/router-control-center/app.js || fetch "${REPO_RAW}/app.js${CACHE_BUST}" /opt/share/router-control-center/app.js

# 5. Настройка ttyd (только loopback 127.0.0.1:7682, публичный порт 7681 защищен прокси)
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

# 6. Запуск служб
/opt/etc/init.d/S96ttyd restart >/dev/null 2>&1 || true
/opt/etc/init.d/S90router-api restart >/dev/null 2>&1

# Определение локального LAN IP роутера (приоритет: локальные мосты br0 / br-lan / br1)
LAN_IP=$(ip -4 addr show br0 2>/dev/null | grep -o 'inet [0-9.]*' | awk '{print $2}')
[ -z "$LAN_IP" ] && LAN_IP=$(ip -4 addr show br-lan 2>/dev/null | grep -o 'inet [0-9.]*' | awk '{print $2}')
[ -z "$LAN_IP" ] && LAN_IP=$(ip -4 addr show br1 2>/dev/null | grep -o 'inet [0-9.]*' | awk '{print $2}')
[ -z "$LAN_IP" ] && LAN_IP=$(ip -4 addr show 2>/dev/null | awk '/inet 192\.168\./{print $2}' | cut -d/ -f1 | head -n1)
[ -z "$LAN_IP" ] && LAN_IP="192.168.1.1"

printf "\n${GREEN}==========================================================${NC}\n"
printf "${GREEN}GRouter Панель успешно установлена и запущена!${NC}\n"
printf "👉 Веб-панель: ${GREEN}http://%s:8089/${NC}\n" "$LAN_IP"
printf "👉 Веб-терминал: ${GREEN}http://%s:7681/${NC} (после входа в панель)\n" "$LAN_IP"
printf "Логин: ${YELLOW}admin${NC}\n"
printf "Пароль: ${YELLOW}Salomanov${NC} (стандартный, менять не обязательно)\n"
printf "${GREEN}==========================================================${NC}\n\n"
exit 0
