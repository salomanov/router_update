#!/bin/sh

# ==========================================================
# Module 04: nfqws Web UI (Port 90)
# - Official nfqws-keenetic-web package
# - Lighttpd + PHP-CGI isolated on port 90
# ==========================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

printf "${GREEN}=== Установка Веб-интерфейса nfqws (порт 90) ===${NC}\n"

if [ "$(id -u)" != "0" ]; then
    printf "${RED}Ошибка: Скрипт должен быть запущен с правами root.${NC}\n"
    exit 1
fi

if [ ! -d "/opt" ] || [ ! -x "/opt/bin/opkg" ]; then
    printf "${RED}Ошибка: Среда Entware (/opt) не найдена на этом роутере.${NC}\n"
    exit 1
fi

export PATH="/opt/bin:/opt/sbin:/bin:/sbin:/usr/bin:/usr/sbin"

# 1. Добавление репозитория
mkdir -p /opt/etc/opkg
echo "src/gz nfqws-keenetic-web https://nfqws.github.io/nfqws-keenetic-web/all" > /opt/etc/opkg/nfqws-keenetic-web.conf

# 2. Установка пакета nfqws-keenetic-web
printf "${YELLOW}Установка пакета nfqws-keenetic-web через OPKG...${NC}\n"
if [ -x "/opt/scripts/opkg_update.py" ]; then
    python3 /opt/scripts/opkg_update.py >/dev/null 2>&1 || opkg update >/dev/null 2>&1
else
    opkg update >/dev/null 2>&1
fi
opkg install nfqws-keenetic-web >/dev/null 2>&1

# 3. Настройка lighttpd строго на порт 90
if [ -d "/opt/etc/lighttpd" ]; then
    mkdir -p /opt/etc/lighttpd/conf.d
    cat << 'EOFLIGHT' > /opt/etc/lighttpd/conf.d/80-nfqws.conf
server.port := 90
cgi.assign += ( ".php" => "/opt/bin/php-cgi" )
static-file.exclude-extensions += ( ".php" )
setenv.set-environment = ( "PATH" => "/opt/sbin:/opt/bin:/opt/usr/sbin:/opt/usr/bin:/usr/sbin:/usr/bin:/sbin:/bin" )
index-file.names := ( "index.html" )
server.error-handler-404 = "/nfqws/index.html"
url.rewrite-once = ( "^/(.*)" => "/nfqws/$1" )
EOFLIGHT
    [ -x "/opt/etc/init.d/S80lighttpd" ] && /opt/etc/init.d/S80lighttpd restart >/dev/null 2>&1 || true
fi

# Определение локального LAN IP роутера (приоритет: локальные мосты br0 / br-lan / br1)
LAN_IP=$(ip -4 addr show br0 2>/dev/null | grep -o 'inet [0-9.]*' | awk '{print $2}')
[ -z "$LAN_IP" ] && LAN_IP=$(ip -4 addr show br-lan 2>/dev/null | grep -o 'inet [0-9.]*' | awk '{print $2}')
[ -z "$LAN_IP" ] && LAN_IP=$(ip -4 addr show br1 2>/dev/null | grep -o 'inet [0-9.]*' | awk '{print $2}')
[ -z "$LAN_IP" ] && LAN_IP=$(ip -4 addr show 2>/dev/null | awk '/inet 192\.168\./{print $2}' | cut -d/ -f1 | head -n1)
[ -z "$LAN_IP" ] && LAN_IP="192.168.1.1"

printf "${GREEN}[OK] Веб-панель nfqws доступна по адресу: http://%s:90/${NC}\n\n" "$LAN_IP"
exit 0
