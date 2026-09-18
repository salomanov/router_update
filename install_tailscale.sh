#!/bin/sh

# ==========================================================
# Tailscale Quick Auto-Installer for Keenetic / Entware
# ==========================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

printf "${GREEN}=== Начинаю быструю установку Tailscale на роутер ===${NC}\n"

# 1. Проверка Entware
if [ ! -d "/opt" ] || [ ! -x "/opt/bin/opkg" ]; then
    printf "${RED}Ошибка: Среда Entware (/opt) не найдена на этом роутере.${NC}\n"
    exit 1
fi

export PATH="/opt/bin:/opt/sbin:/bin:/sbin:/usr/bin:/usr/sbin"

# 2. Подготовка системных каталогов и TUN-драйвера
printf "${YELLOW}[1/5] Настройка TUN-интерфейса и IP Forwarding...${NC}\n"
mkdir -p /dev/net /opt/var/lib/tailscale /opt/var/run/tailscale /opt/var/log /opt/etc/init.d /opt/etc/ndm/netfilter.d
if [ ! -c /dev/net/tun ]; then
    mknod /dev/net/tun c 10 200
fi
sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1
sysctl -w net.ipv6.conf.all.forwarding=1 >/dev/null 2>&1

# 3. Добавление доменов Tailscale в белый список nfqws2
printf "${YELLOW}[2/5] Добавление Tailscale в список обхода DPI (nfqws2)...${NC}\n"
USER_LIST="/opt/etc/nfqws2/lists/user.list"
if [ -f "$USER_LIST" ]; then
    for d in tailscale.com controlplane.tailscale.com login.tailscale.com log.tailscale.io pkgs.tailscale.com derp.tailscale.com; do
        grep -q "$d" "$USER_LIST" || echo "$d" >> "$USER_LIST"
    done
    sort -u "$USER_LIST" -o "$USER_LIST"
    [ -x "/opt/etc/init.d/S51nfqws2" ] && /opt/etc/init.d/S51nfqws2 restart >/dev/null 2>&1
fi

# 4. Установка пакета Tailscale
printf "${YELLOW}[3/5] Установка пакета Tailscale через OPKG...${NC}\n"
killall opkg 2>/dev/null
rm -f /opt/tmp/opkg.lock
opkg update >/dev/null 2>&1
opkg install tailscale >/dev/null 2>&1

if [ ! -x "/opt/bin/tailscaled" ]; then
    printf "${RED}Ошибка: Не удалось установить Tailscale через opkg.${NC}\n"
    exit 1
fi

# 5. Создание скрипта автозапуска S06tailscale
printf "${YELLOW}[4/5] Настройка автозапуска службы tailscaled...${NC}\n"
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
    sysctl -w net.ipv6.conf.all.forwarding=1 >/dev/null 2>&1
    
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

# 6. Настройка постоянных правил iptables
cat << 'EOF' > /opt/etc/ndm/netfilter.d/010-tailscale.sh
#!/bin/sh
iptables -C INPUT -i tailscale0 -j ACCEPT 2>/dev/null || iptables -I INPUT -i tailscale0 -j ACCEPT
iptables -C FORWARD -i tailscale0 -j ACCEPT 2>/dev/null || iptables -I FORWARD -i tailscale0 -j ACCEPT
iptables -C FORWARD -o tailscale0 -j ACCEPT 2>/dev/null || iptables -I FORWARD -o tailscale0 -j ACCEPT

# Reject QUIC (UDP 443) from tailscale0 immediately to force mobile apps (Instagram, YouTube) to fallback to TCP with DPI bypass instantly
iptables -C FORWARD -i tailscale0 -p udp --dport 443 -j REJECT --reject-with icmp-port-unreachable 2>/dev/null || iptables -I FORWARD -i tailscale0 -p udp --dport 443 -j REJECT --reject-with icmp-port-unreachable

# Clamp TCP MSS for Tailscale (MTU 1280) to 1240 to prevent packet drops and fragmentation
iptables -t mangle -C FORWARD -o tailscale0 -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1240 2>/dev/null || iptables -t mangle -I FORWARD -o tailscale0 -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1240
iptables -t mangle -C FORWARD -i tailscale0 -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1240 2>/dev/null || iptables -t mangle -I FORWARD -i tailscale0 -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1240

# Reject IPv6 forwarding from tailscale0 immediately to eliminate Happy Eyeballs timeouts on Android
ip6tables -C FORWARD -i tailscale0 -j REJECT --reject-with icmp6-port-unreachable 2>/dev/null || ip6tables -I FORWARD -i tailscale0 -j REJECT --reject-with icmp6-port-unreachable

# NAT masquerade for Exit Node
iptables -t nat -C POSTROUTING -s 100.64.0.0/10 -j MASQUERADE 2>/dev/null || iptables -t nat -I POSTROUTING -s 100.64.0.0/10 -j MASQUERADE
iptables -t nat -C POSTROUTING -o ppp0 -j MASQUERADE 2>/dev/null || iptables -t nat -I POSTROUTING -o ppp0 -j MASQUERADE
EOF
chmod +x /opt/etc/ndm/netfilter.d/010-tailscale.sh
/opt/etc/ndm/netfilter.d/010-tailscale.sh

# 7. Запуск службы и генерация ссылки
printf "${YELLOW}[5/5] Запуск Tailscale и получение ссылки авторизации...${NC}\n"
/opt/etc/init.d/S06tailscale restart >/dev/null 2>&1
sleep 3

printf "\n${GREEN}==========================================================${NC}\n"
printf "${GREEN}Tailscale успешно установлен и запущен!${NC}\n"
printf "${GREEN}Для привязки роутера перейдите по ссылке ниже:${NC}\n"
printf "${GREEN}==========================================================${NC}\n\n"

/opt/bin/tailscale --socket=/opt/var/run/tailscale/tailscaled.sock up --advertise-exit-node --advertise-routes=192.168.1.0/24 --accept-dns=false --accept-routes=false --reset --timeout=20s
