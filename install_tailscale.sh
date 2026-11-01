#!/bin/sh

# ==========================================================
# Tailscale Quick Auto-Installer for Keenetic / Entware
# ==========================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

printf "${GREEN}=== Установка Tailscale на роутер ===${NC}\n"

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

# 3. Настройка TUN-интерфейса и IP Forwarding
printf "${YELLOW}[1/4] Настройка TUN-интерфейса и сетевого форвардинга...${NC}\n"
mkdir -p /dev/net /opt/var/lib/tailscale /opt/var/run/tailscale /opt/var/log /opt/etc/init.d /opt/etc/ndm/netfilter.d
if [ ! -c /dev/net/tun ]; then
    mknod /dev/net/tun c 10 200
fi
sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1
sysctl -w net.ipv6.conf.all.forwarding=0 >/dev/null 2>&1

# 4. Установка пакета Tailscale через OPKG
printf "${YELLOW}[2/4] Установка пакета tailscale...${NC}\n"
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

# Удаление конфликтующего стандартного init-скрипта opkg и создание симлинка состояния
rm -f /opt/etc/init.d/S06tailscaled 2>/dev/null
mkdir -p /opt/var/lib/tailscale
ln -sf /opt/var/lib/tailscale/tailscaled.state /opt/var/tailscaled.state 2>/dev/null || true

# 5. Создание скрипта автозапуска S06tailscale
printf "${YELLOW}[3/4] Настройка автозапуска службы tailscaled...${NC}\n"
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

# 6. Настройка постоянных правил iptables для Tailscale
REPO_RAW="https://raw.githubusercontent.com/salomanov/router_update/main/configs"
CACHE_BUST="?nocache=$(date +%s)$$"
curl -fsSL --max-time 30 -o /opt/etc/ndm/netfilter.d/010-tailscale.sh "${REPO_RAW}/ndm/010-tailscale.sh${CACHE_BUST}" 2>/dev/null || true
if [ -s "/opt/etc/ndm/netfilter.d/010-tailscale.sh" ]; then
    chmod +x /opt/etc/ndm/netfilter.d/010-tailscale.sh
    /opt/etc/ndm/netfilter.d/010-tailscale.sh >/dev/null 2>&1 || true
fi

# 7. Запуск службы
printf "${YELLOW}[4/4] Запуск службы Tailscale...${NC}\n"
/opt/etc/init.d/S06tailscale restart >/dev/null 2>&1
sleep 2

if pgrep tailscaled >/dev/null; then
    printf "\n${GREEN}==========================================================${NC}\n"
    printf "${GREEN}Tailscale успешно установлен и запущен!${NC}\n"
    printf "Для авторизации роутера в вашей сети Tailscale выполните:\n"
    printf "${YELLOW}/opt/bin/tailscale up${NC}\n"
    printf "Или с правами Exit Node:\n"
    printf "${YELLOW}/opt/bin/tailscale up --advertise-exit-node --accept-routes${NC}\n"
    printf "${GREEN}==========================================================${NC}\n\n"
else
    printf "${RED}Ошибка запуска tailscaled. Проверьте логи /opt/var/log/tailscaled.log${NC}\n"
    exit 1
fi
