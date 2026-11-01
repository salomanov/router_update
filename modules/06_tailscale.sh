#!/bin/sh

# ==========================================================
# Module 06: Tailscale Mesh VPN & Exit Node
# - Installs tailscale and configures TUN & iptables
# - Creates /opt/bin/tailscale-status for easy status & login URL recall
# ==========================================================

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

show_status() {
    printf "${CYAN}=== Статус Tailscale VPN ===${NC}\n"
    if pgrep tailscaled >/dev/null 2>&1; then
        printf "Служба tailscaled: ${GREEN}Работает${NC}\n"
    else
        printf "Служба tailscaled: ${RED}Остановлена${NC}\n"
        return 1
    fi

    if [ -x "/opt/bin/tailscale" ]; then
        STATUS_OUT=$(/opt/bin/tailscale status 2>&1)
        IP_OUT=$(/opt/bin/tailscale ip -4 2>/dev/null)
        if [ -n "$IP_OUT" ]; then
            printf "Авторизация: ${GREEN}Успешно подключен${NC}\n"
            printf "Tailscale IP: ${YELLOW}%s${NC}\n" "$IP_OUT"
            printf "\nТекущие узлы в сети Tailscale:\n"
            echo "$STATUS_OUT" | head -n 10
        else
            printf "Авторизация: ${YELLOW}Требуется вход${NC}\n\n"
            printf "Для авторизации или получения ссылки выполните:\n"
            printf "👉 ${GREEN}/opt/bin/tailscale up --advertise-exit-node --accept-routes${NC}\n"
        fi
    fi
    printf "\n"
}

if [ "$1" = "--status" ] || [ "$1" = "status" ]; then
    show_status
    exit 0
fi

printf "${GREEN}=== Установка Tailscale (VPN Exit Node) ===${NC}\n"

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

# 2. Настройка TUN-интерфейса и IP Forwarding
mkdir -p /dev/net /opt/var/lib/tailscale /opt/var/run/tailscale /opt/var/log /opt/etc/init.d /opt/etc/ndm/netfilter.d
if [ ! -c /dev/net/tun ]; then
    mknod /dev/net/tun c 10 200
fi
sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1
sysctl -w net.ipv6.conf.all.forwarding=0 >/dev/null 2>&1

# 3. Установка пакета Tailscale через OPKG
printf "${YELLOW}Установка пакета tailscale через OPKG...${NC}\n"
if [ -x "/opt/scripts/opkg_update.py" ]; then
    python3 /opt/scripts/opkg_update.py >/dev/null 2>&1 || opkg update >/dev/null 2>&1
else
    opkg update >/dev/null 2>&1
fi
opkg install tailscale >/dev/null 2>&1

if [ ! -x "/opt/bin/tailscaled" ]; then
    printf "${RED}Ошибка: Не удалось установить Tailscale через opkg.${NC}\n"
    exit 1
fi

# 4. Настройка автозапуска службы S06tailscale
rm -f /opt/etc/init.d/S06tailscaled 2>/dev/null
ln -sf /opt/var/lib/tailscale/tailscaled.state /opt/var/tailscaled.state 2>/dev/null || true

cat << 'EOF' > /opt/etc/init.d/S06tailscale
#!/bin/sh

ENABLED=yes
PROCS=tailscaled
ARGS="--state=/opt/var/lib/tailscale/tailscaled.state --socket=/opt/var/run/tailscale/tailscaled.sock --port=41641"
DESC=$PROCS
PATH=/opt/sbin:/opt/bin:/opt/usr/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

start() {
    mkdir -p /dev/net /opt/var/lib/tailscale /opt/var/run/tailscale /opt/var/log
    if [ ! -c /dev/net/tun ]; then
        mknod /dev/net/tun c 10 200
    fi
    sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1
    sysctl -w net.ipv6.conf.all.forwarding=0 >/dev/null 2>&1
    
    echo -n "Starting $DESC... "
    start-stop-daemon -S -b -m -p /opt/var/run/tailscaled.pid -x /opt/bin/tailscaled -- $ARGS
    echo "done."
}

stop() {
    echo -n "Stopping $DESC... "
    start-stop-daemon -K -p /opt/var/run/tailscaled.pid -s TERM 2>/dev/null
    killall tailscaled 2>/dev/null
    rm -f /opt/var/run/tailscaled.pid
    echo "done."
}

case "$1" in
    start) start ;;
    stop) stop ;;
    restart) stop; sleep 1; start ;;
    *) echo "Usage: $0 {start|stop|restart}"; exit 1 ;;
esac
EOF
chmod +x /opt/etc/init.d/S06tailscale

# 5. Установка постоянных правил iptables для Tailscale
REPO_RAW="https://raw.githubusercontent.com/salomanov/router_update/main"
CACHE_BUST="?nocache=$(date +%s)$$"
curl -fsSL --max-time 30 -o /opt/etc/ndm/netfilter.d/010-tailscale.sh "${REPO_RAW}/netfilter/010-tailscale.sh${CACHE_BUST}" 2>/dev/null || true
if [ -s "/opt/etc/ndm/netfilter.d/010-tailscale.sh" ]; then
    chmod +x /opt/etc/ndm/netfilter.d/010-tailscale.sh
    /opt/etc/ndm/netfilter.d/010-tailscale.sh >/dev/null 2>&1 || true
fi

# 6. Создание вспомогательной утилиты /opt/bin/tailscale-status
cat << 'EOFTS' > /opt/bin/tailscale-status
#!/bin/sh
sh /opt/scripts/modules/06_tailscale.sh --status 2>/dev/null || /opt/bin/tailscale status
EOFTS
chmod 755 /opt/bin/tailscale-status 2>/dev/null || true

# 7. Запуск службы
/opt/etc/init.d/S06tailscale restart >/dev/null 2>&1
sleep 2

printf "${GREEN}[OK] Служба Tailscale успешно установлена и запущена!${NC}\n\n"
show_status
printf "Команда для проверки статуса в любое время: ${YELLOW}tailscale-status${NC}\n\n"
exit 0
