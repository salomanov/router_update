#!/bin/sh

# ==========================================================
# Module 05: Telegram MTProto WebSocket Proxy (Port 1443)
# - Installs tg-ws-proxy from feedly
# - Creates /opt/bin/tg-proxy-link for instant status & link recall
# ==========================================================

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

show_status() {
    printf "${CYAN}=== Статус Telegram Proxy (tg-ws-proxy) ===${NC}\n"
    if pgrep tg-ws-proxy >/dev/null 2>&1; then
        PID=$(pidof tg-ws-proxy)
        printf "Статус: ${GREEN}Работает (PID: %s)${NC}\n" "$PID"
    else
        printf "Статус: ${RED}Остановлен${NC}\n"
    fi

    SECRET=""
    PORT="1443"
    [ -f "/opt/etc/tg-ws-proxy/secret.conf" ] && SECRET=$(grep -E '^SECRET=' /opt/etc/tg-ws-proxy/secret.conf 2>/dev/null | cut -d'=' -f2 | tr -d '\r\n')
    [ -f "/opt/etc/tg-ws-proxy/config.conf" ] && PORT=$(grep -E '^PORT=' /opt/etc/tg-ws-proxy/config.conf 2>/dev/null | cut -d'=' -f2 | tr -d '\r\n')
    [ -z "$PORT" ] && PORT="1443"

    LAN_IP=$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}')
    [ -z "$LAN_IP" ] && LAN_IP=$(ip -4 addr show br0 2>/dev/null | grep -o 'inet [0-9.]*' | awk '{print $2}')
    [ -z "$LAN_IP" ] && LAN_IP="192.168.1.1"

    WAN_IP=$(curl -s --max-time 3 ifconfig.me 2>/dev/null || curl -s --max-time 3 icanhazip.com 2>/dev/null)

    printf "Порт:   ${YELLOW}%s${NC}\n" "$PORT"
    printf "Секрет: ${YELLOW}%s${NC}\n\n" "$SECRET"

    if [ -n "$SECRET" ]; then
        printf "Локальная ссылка (в домашней сети):\n"
        printf "👉 ${GREEN}tg://proxy?server=%s&port=%s&secret=%s${NC}\n" "$LAN_IP" "$PORT" "$SECRET"
        printf "👉 https://t.me/proxy?server=%s&port=%s&secret=%s\n\n" "$LAN_IP" "$PORT" "$SECRET"

        if [ -n "$WAN_IP" ]; then
            printf "Внешняя ссылка (через интернет, если проброшен порт 1443):\n"
            printf "👉 ${GREEN}tg://proxy?server=%s&port=%s&secret=%s${NC}\n" "$WAN_IP" "$PORT" "$SECRET"
            printf "👉 https://t.me/proxy?server=%s&port=%s&secret=%s\n\n" "$WAN_IP" "$PORT" "$SECRET"
        fi
    fi
}

if [ "$1" = "--status" ] || [ "$1" = "status" ] || [ "$1" = "--link" ]; then
    show_status
    exit 0
fi

printf "${GREEN}=== Установка Telegram Proxy (tg-ws-proxy) ===${NC}\n"

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

# 2. Добавление репозитория feedly
mkdir -p /opt/etc/opkg
echo "src/gz feedly_mipsel-3.4 https://spatiumstas.github.io/feedly/mipsel-3.4" > /opt/etc/opkg/feedly.conf

# 3. Установка пакета tg-ws-proxy
printf "${YELLOW}Установка пакета tg-ws-proxy через OPKG...${NC}\n"
if [ -x "/opt/scripts/opkg_update.py" ]; then
    python3 /opt/scripts/opkg_update.py >/dev/null 2>&1 || opkg update >/dev/null 2>&1
else
    opkg update >/dev/null 2>&1
fi
opkg install tg-ws-proxy >/dev/null 2>&1

if [ ! -x "/opt/bin/tg-ws-proxy" ]; then
    printf "${RED}Ошибка: Не удалось установить tg-ws-proxy.${NC}\n"
    exit 1
fi

# 4. Создание вспомогательной утилиты /opt/bin/tg-proxy-link
cat << 'EOFLINK' > /opt/bin/tg-proxy-link
#!/bin/sh
sh /opt/scripts/modules/05_tg_proxy.sh --status 2>/dev/null || {
    SECRET=$(grep -E '^SECRET=' /opt/etc/tg-ws-proxy/secret.conf 2>/dev/null | cut -d'=' -f2 | tr -d '\r\n')
    PORT=$(grep -E '^PORT=' /opt/etc/tg-ws-proxy/config.conf 2>/dev/null | cut -d'=' -f2 | tr -d '\r\n')
    [ -z "$PORT" ] && PORT="1443"
    LAN_IP=$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}')
    [ -z "$LAN_IP" ] && LAN_IP="192.168.1.1"
    echo "Ссылка для подключения: tg://proxy?server=${LAN_IP}&port=${PORT}&secret=${SECRET}"
}
EOFLINK
chmod 755 /opt/bin/tg-proxy-link 2>/dev/null || true

# 5. Запуск службы
if [ -x "/opt/etc/init.d/S99tg-ws-proxy" ]; then
    /opt/etc/init.d/S99tg-ws-proxy restart >/dev/null 2>&1
    printf "${GREEN}[OK] tg-ws-proxy запущен на порту 1443.${NC}\n\n"
fi

show_status
printf "Команда для просмотра ссылки в любое время: ${YELLOW}tg-proxy-link${NC}\n\n"
exit 0
