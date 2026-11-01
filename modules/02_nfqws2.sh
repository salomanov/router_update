#!/bin/sh

# ==========================================================
# Module 02: nfqws2 Anti-DPI & Web UI (Port 90)
# - Official nfqws2-keenetic + nfqws-keenetic-web packages
# - Standard circular multisplit profile (out of the box)
# - Lighttpd isolated on port 90
# ==========================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

printf "${GREEN}=== [2/5] Установка nfqws2 Anti-DPI и Web UI ===${NC}\n"

if [ "$(id -u)" != "0" ]; then
    printf "${RED}Ошибка: Скрипт должен быть запущен с правами root.${NC}\n"
    exit 1
fi

if [ ! -d "/opt" ] || [ ! -x "/opt/bin/opkg" ]; then
    printf "${RED}Ошибка: Среда Entware (/opt) не найдена на этом роутере.${NC}\n"
    exit 1
fi

export PATH="/opt/bin:/opt/sbin:/bin:/sbin:/usr/bin:/usr/sbin"

# 1. Безопасная очистка зависшего лока opkg (без killall)
if [ -f "/opt/tmp/opkg.lock" ]; then
    if ! pgrep opkg >/dev/null 2>&1; then
        rm -f "/opt/tmp/opkg.lock"
    fi
fi

# 2. Добавление официальных репозиториев nfqws
printf "${YELLOW}Настройка официальных репозиториев nfqws...${NC}\n"
mkdir -p /opt/etc/opkg
echo "src/gz nfqws2-keenetic https://nfqws.github.io/nfqws2-keenetic/all" > /opt/etc/opkg/nfqws2-keenetic.conf
echo "src/gz nfqws-keenetic-web https://nfqws.github.io/nfqws-keenetic-web/all" > /opt/etc/opkg/nfqws-keenetic-web.conf

# 3. Обновление списков пакетов (устойчиво к блокировкам)
printf "${YELLOW}Установка пакетов nfqws2-keenetic и nfqws-keenetic-web...${NC}\n"
if [ -x "/opt/scripts/opkg_update.py" ]; then
    python3 /opt/scripts/opkg_update.py >/dev/null 2>&1 || opkg update >/dev/null 2>&1
else
    opkg update >/dev/null 2>&1
fi
opkg install nfqws2-keenetic nfqws-keenetic-web >/dev/null 2>&1

if [ ! -x "/opt/usr/bin/nfqws2" ]; then
    printf "${RED}Ошибка: Бинарный файл /opt/usr/bin/nfqws2 не найден после установки.${NC}\n"
    exit 1
fi

# 4. Автоопределение активного WAN-интерфейса роутера
DEF_IFACE=$(route -n 2>/dev/null | awk '$1=="0.0.0.0"{print $8; exit}')
[ -z "$DEF_IFACE" ] && DEF_IFACE=$(ip route show default 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="dev") {print $(i+1); exit}}')
if [ -n "$DEF_IFACE" ] && [ -f "/opt/etc/nfqws2/nfqws2.conf" ]; then
    printf "Интернет-интерфейс: %s\n" "$DEF_IFACE"
    sed -i -E "s#^ISP_INTERFACE=\".+\"#ISP_INTERFACE=\"$DEF_IFACE\"#" /opt/etc/nfqws2/nfqws2.conf
fi

# 5. Изоляция lighttpd для nfqws-web строго на порту 90
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

# 6. Запуск nfqws2
if [ -x "/opt/etc/init.d/S51nfqws2" ]; then
    /opt/etc/init.d/S51nfqws2 restart >/dev/null 2>&1
    printf "${GREEN}[OK] nfqws2 и Web UI (порт 90) успешно запущены!${NC}\n\n"
fi
exit 0
