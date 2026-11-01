#!/bin/sh

# ==========================================================
# nfqws2 Anti-DPI Auto-Installer for Keenetic / Entware
# Upstream-first: official nfqws2-keenetic package + web UI (port 90)
# + Netfilter rules for LAN DNS redirect, QUIC block, MSS clamp
# ==========================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

printf "${GREEN}=== Установка обхода блокировок (nfqws2) ===${NC}\n"

# 1. Проверка Entware
if [ ! -d "/opt" ] || [ ! -x "/opt/bin/opkg" ]; then
    printf "${RED}Ошибка: Среда Entware (/opt) не найдена на этом роутере.${NC}\n"
    exit 1
fi

export PATH="/opt/bin:/opt/sbin:/bin:/sbin:/usr/bin:/usr/sbin"

# 2. Безопасная очистка зависших локов opkg (без killall)
if [ -f "/opt/tmp/opkg.lock" ]; then
    if ! pgrep opkg >/dev/null 2>&1; then
        rm -f "/opt/tmp/opkg.lock"
    fi
fi

# 3. Добавление официальных репозиториев nfqws2
printf "${YELLOW}[1/4] Настройка репозиториев nfqws2...${NC}\n"
mkdir -p /opt/etc/opkg
echo "src/gz nfqws2-keenetic https://nfqws.github.io/nfqws2-keenetic/all" > /opt/etc/opkg/nfqws2-keenetic.conf
echo "src/gz nfqws-keenetic-web https://nfqws.github.io/nfqws-keenetic-web/all" > /opt/etc/opkg/nfqws-keenetic-web.conf

# 4. Обновление списков пакетов (устойчиво к DPI)
printf "${YELLOW}[2/4] Установка пакетов nfqws2-keenetic и nfqws-keenetic-web...${NC}\n"
if [ -x "/opt/scripts/opkg_update.py" ]; then
    python3 /opt/scripts/opkg_update.py >/dev/null 2>&1 || opkg update >/dev/null 2>&1
else
    opkg update >/dev/null 2>&1
fi
opkg install nfqws2-keenetic nfqws-keenetic-web >/dev/null 2>&1

if [ ! -x "/opt/usr/bin/nfqws2" ]; then
    printf "${RED}Ошибка: Не удалось установить nfqws2-keenetic через opkg.${NC}\n"
    exit 1
fi

# 5. Загрузка сетевых правил (NDM netfilter hooks)
printf "${YELLOW}[3/4] Установка сетевых правил (DNS redirect, QUIC block, MSS clamp)...${NC}\n"
mkdir -p /opt/etc/ndm/netfilter.d
REPO_RAW="https://raw.githubusercontent.com/salomanov/router_update/main/configs"
CACHE_BUST="?nocache=$(date +%s)$$"

fetch() {
    curl -fsSL --max-time 30 -o "$2" "$1" 2>/dev/null || true
    [ -s "$2" ] && chmod +x "$2"
}

# Сетевые правила для LAN (перехват DNS, сброс мертвого IPv6, сжатие MSS)
fetch "${REPO_RAW}/ndm/005-lan-fix.sh${CACHE_BUST}" /opt/etc/ndm/netfilter.d/005-lan-fix.sh
# Сетевые правила для L2TP VPN клиентов
fetch "${REPO_RAW}/ndm/015-l2tp.sh${CACHE_BUST}" /opt/etc/ndm/netfilter.d/015-l2tp.sh
# Блокировка QUIC
fetch "${REPO_RAW}/ndm/020-block-quic.sh${CACHE_BUST}" /opt/etc/ndm/netfilter.d/020-block-quic.sh

# Запуск сетевых правил
[ -x "/opt/etc/ndm/netfilter.d/005-lan-fix.sh" ] && /opt/etc/ndm/netfilter.d/005-lan-fix.sh >/dev/null 2>&1 || true
[ -x "/opt/etc/ndm/netfilter.d/015-l2tp.sh" ] && /opt/etc/ndm/netfilter.d/015-l2tp.sh >/dev/null 2>&1 || true
[ -x "/opt/etc/ndm/netfilter.d/020-block-quic.sh" ] && /opt/etc/ndm/netfilter.d/020-block-quic.sh >/dev/null 2>&1 || true

# Автоопределение активного WAN-интерфейса роутера
DEF_IFACE=$(route -n 2>/dev/null | awk '$1=="0.0.0.0"{print $8; exit}')
[ -z "$DEF_IFACE" ] && DEF_IFACE=$(ip route show default 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="dev") {print $(i+1); exit}}')
if [ -n "$DEF_IFACE" ] && [ -f "/opt/etc/nfqws2/nfqws2.conf" ]; then
    printf "Интернет-интерфейс: %s\n" "$DEF_IFACE"
    sed -i -E "s#^ISP_INTERFACE=\".+\"#ISP_INTERFACE=\"$DEF_IFACE\"#" /opt/etc/nfqws2/nfqws2.conf
fi

# Настройка веб-интерфейса nfqws-web на порту 90 (lighttpd)
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

# 6. Запуск и проверка службы
printf "${YELLOW}[4/4] Запуск службы nfqws2...${NC}\n"
if [ -x "/opt/etc/init.d/S51nfqws2" ]; then
    /opt/etc/init.d/S51nfqws2 restart >/dev/null 2>&1
    sleep 2
    if pgrep nfqws2 >/dev/null || pgrep nfqws >/dev/null; then
        LAN_IP=$(ip -4 addr show br0 2>/dev/null | grep -o 'inet [0-9.]*' | awk '{print $2}')
        [ -z "$LAN_IP" ] && LAN_IP="192.168.1.1"
        printf "\n${GREEN}==========================================================${NC}\n"
        printf "${GREEN}nfqws2 успешно установлен и запущен!${NC}\n"
        printf "${GREEN}Веб-интерфейс nfqws: http://%s:90/${NC}\n" "$LAN_IP"
        printf "${GREEN}==========================================================${NC}\n\n"
        exit 0
    fi
fi

printf "${YELLOW}nfqws2 установлен, проверьте статус через веб-панель.${NC}\n"
