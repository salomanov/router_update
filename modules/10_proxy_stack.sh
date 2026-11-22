#!/bin/sh

# ==========================================================
# Module 10: Unified Proxy Stack (sing-box & Netfilter Dispatcher)
# - Transparent TCP redirect & UDP tproxy on port 10080 -> Usque MASQUE :8480
# - Deploys /opt/etc/ndm/netfilter.d/010-proxy.sh
# - Deploys /opt/scripts/update_ipsets.sh with cron automation
# ==========================================================

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
GRAY='\033[0;37m'
NC='\033[0m'

show_status() {
    printf "${CYAN}=== Статус стека прозрачного проксирования (Proxy Stack) ===${NC}\n"
    
    # 1. sing-box daemon
    if pidof sing-box >/dev/null 2>&1; then
        PID=$(pidof sing-box)
        printf "Служба sing-box:   ${GREEN}Работает (PID: %s)${NC}\n" "$PID"
    elif [ -f "/opt/var/run/redsocks.pid" ] && kill -0 "$(cat /opt/var/run/redsocks.pid 2>/dev/null)" 2>/dev/null; then
        PID=$(cat /opt/var/run/redsocks.pid)
        printf "Служба redsocks:   ${YELLOW}Работает (фолбэк, PID: %s)${NC}\n" "$PID"
    else
        printf "Прокси-ядро:       ${RED}Остановлено${NC}\n"
    fi

    # 2. Port check
    if netstat -tuln 2>/dev/null | grep -q ':10080 '; then
        printf "Порт редиректа:    ${GREEN}:10080 (sing-box UP)${NC}\n"
    elif netstat -tuln 2>/dev/null | grep -q ':12345 '; then
        printf "Порт редиректа:    ${YELLOW}:12345 (redsocks UP)${NC}\n"
    else
        printf "Порт редиректа:    ${RED}Закрыт${NC}\n"
    fi

    # 3. Netfilter hook
    if [ -x "/opt/etc/ndm/netfilter.d/010-proxy.sh" ]; then
        ACTIVE_RULES=$(iptables -t nat -S REDSOCKS_TG 2>/dev/null | grep -c 'REDIRECT')
        printf "Netfilter хук:     ${GREEN}Установлен (/opt/etc/ndm/netfilter.d/010-proxy.sh)${NC}\n"
        printf "Правила nat/TG:    ${GREEN}%s активных редиректов${NC}\n" "$ACTIVE_RULES"
    else
        printf "Netfilter хук:     ${RED}Не установлен${NC}\n"
    fi

    # 4. IPSET lists
    if command -v ipset >/dev/null 2>&1; then
        AI_CNT=$(ipset list AI_NETS 2>/dev/null | grep -c '^[0-9]')
        META_CNT=$(ipset list META_NETS 2>/dev/null | grep -c '^[0-9]')
        printf "Ипсет AI_NETS:     ${GREEN}%s IP-адресов${NC}\n" "$AI_CNT"
        printf "Ипсет META_NETS:   ${GREEN}%s суперсетей AS32934${NC}\n" "$META_CNT"
    else
        printf "Утилита ipset:     ${RED}Не установлена${NC}\n"
    fi

    # 5. Usque uplink
    if pidof usque >/dev/null 2>&1; then
        printf "Апстрим usque:     ${GREEN}Активен (:8480)${NC}\n"
    else
        printf "Апстрим usque:     ${YELLOW}Не обнаружен на :8480 (проверьте S99usque)${NC}\n"
    fi
    printf "\n"
}

if [ "$1" = "--status" ] || [ "$1" = "status" ]; then
    show_status
    exit 0
fi

printf "${GREEN}=== Установка стека проксирования (sing-box + 010-proxy) ===${NC}\n"

if [ "$(id -u)" != "0" ]; then
    printf "${RED}Ошибка: Скрипт должен быть запущен с правами root.${NC}\n"
    exit 1
fi

if [ ! -d "/opt" ] || [ ! -x "/opt/bin/opkg" ]; then
    printf "${RED}Ошибка: Среда Entware (/opt) не найдена на этом роутере.${NC}\n"
    exit 1
fi

export PATH="/opt/sbin:/opt/bin:/opt/usr/bin:/usr/sbin:/usr/bin:/sbin:/bin"
REPO_RAW="https://raw.githubusercontent.com/salomanov/router_update/main"
CACHE_BUST="?nocache=$(date +%s)$$"
SCRIPT_DIR="$(dirname "$0")"

# 1. Безопасная очистка зависшего лока opkg (без killall)
if [ -f "/opt/tmp/opkg.lock" ]; then
    if ! pgrep opkg >/dev/null 2>&1; then
        rm -f "/opt/tmp/opkg.lock"
    fi
fi

# 2. Установка пакетов ipset, iptables и sing-box-go
printf "${YELLOW}[1/6] Проверка и установка пакетов (ipset, iptables, sing-box-go)...${NC}\n"
need_pkg=""
command -v ipset >/dev/null 2>&1 || need_pkg="$need_pkg ipset"
command -v iptables >/dev/null 2>&1 || need_pkg="$need_pkg iptables"
[ ! -x "/opt/bin/sing-box" ] && need_pkg="$need_pkg sing-box-go"

if [ -n "$need_pkg" ]; then
    printf "Установка недостающих пакетов:%s\n" "$need_pkg"
    opkg update >/dev/null 2>&1
    for p in $need_pkg; do
        opkg install "$p" >/dev/null 2>&1
    done
fi

# 3. Конфигурация sing-box
printf "${YELLOW}[2/6] Развертывание конфигурации sing-box (/opt/etc/sing-box/config.json)...${NC}\n"
mkdir -p /opt/etc/sing-box
if [ -f "$SCRIPT_DIR/../configs/sing-box/config.json" ]; then
    cp -f "$SCRIPT_DIR/../configs/sing-box/config.json" /opt/etc/sing-box/config.json
elif [ -f "./configs/sing-box/config.json" ]; then
    cp -f "./configs/sing-box/config.json" /opt/etc/sing-box/config.json
else
    curl -fsSL --max-time 30 -o /opt/etc/sing-box/config.json "${REPO_RAW}/configs/sing-box/config.json${CACHE_BUST}" 2>/dev/null || true
fi

# Фолбэк генерация конфига, если файл отсутствует
if [ ! -s "/opt/etc/sing-box/config.json" ]; then
    cat << 'EOF_SB' > /opt/etc/sing-box/config.json
{
  "log": {
    "level": "info",
    "timestamp": true
  },
  "inbounds": [
    {
      "type": "redirect",
      "tag": "redirect-in",
      "listen": "0.0.0.0",
      "listen_port": 10080
    },
    {
      "type": "tproxy",
      "tag": "tproxy-in",
      "listen": "0.0.0.0",
      "listen_port": 10080,
      "network": "udp"
    }
  ],
  "outbounds": [
    {
      "type": "socks",
      "tag": "usque-out",
      "server": "192.168.1.1",
      "server_port": 8480
    },
    {
      "type": "direct",
      "tag": "direct"
    }
  ],
  "route": {
    "rules": [
      {
        "ip_is_private": true,
        "outbound": "direct"
      }
    ],
    "auto_detect_interface": true
  }
}
EOF_SB
fi

# 4. Развертывание NDM хука 010-proxy.sh
printf "${YELLOW}[3/6] Установка NDM netfilter хука (/opt/etc/ndm/netfilter.d/010-proxy.sh)...${NC}\n"
mkdir -p /opt/etc/ndm/netfilter.d
if [ -f "$SCRIPT_DIR/../netfilter/010-proxy.sh" ]; then
    cp -f "$SCRIPT_DIR/../netfilter/010-proxy.sh" /opt/etc/ndm/netfilter.d/010-proxy.sh
elif [ -f "./netfilter/010-proxy.sh" ]; then
    cp -f "./netfilter/010-proxy.sh" /opt/etc/ndm/netfilter.d/010-proxy.sh
else
    curl -fsSL --max-time 30 -o /opt/etc/ndm/netfilter.d/010-proxy.sh "${REPO_RAW}/netfilter/010-proxy.sh${CACHE_BUST}" 2>/dev/null || true
fi
chmod +x /opt/etc/ndm/netfilter.d/010-proxy.sh 2>/dev/null || true

# 5. Развертывание атомарного обновления IPSET
printf "${YELLOW}[4/6] Установка скрипта обновления IPSET (/opt/scripts/update_ipsets.sh)...${NC}\n"
mkdir -p /opt/scripts
if [ -f "$SCRIPT_DIR/../scripts/update_ipsets.sh" ]; then
    cp -f "$SCRIPT_DIR/../scripts/update_ipsets.sh" /opt/scripts/update_ipsets.sh
elif [ -f "./scripts/update_ipsets.sh" ]; then
    cp -f "./scripts/update_ipsets.sh" /opt/scripts/update_ipsets.sh
else
    curl -fsSL --max-time 30 -o /opt/scripts/update_ipsets.sh "${REPO_RAW}/scripts/update_ipsets.sh${CACHE_BUST}" 2>/dev/null || true
fi
chmod +x /opt/scripts/update_ipsets.sh 2>/dev/null || true

# Настройка расписания cron
mkdir -p /opt/var/spool/cron/crontabs
CRON_FILE="/opt/var/spool/cron/crontabs/root"
CRON_LINE="15 */4 * * * /opt/scripts/update_ipsets.sh >/dev/null 2>&1"
touch "$CRON_FILE"
if ! grep -q "update_ipsets.sh" "$CRON_FILE" 2>/dev/null; then
    echo "$CRON_LINE" >> "$CRON_FILE"
    printf "Добавлена задача обновления IPSET в cron: каждые 4 часа.\n"
fi

# 6. Запуск службы sing-box
printf "${YELLOW}[5/6] Запуск службы sing-box...${NC}\n"
# Создаем надежный init-скрипт S99sing-box, если отсутствует
if [ ! -x "/opt/etc/init.d/S99sing-box" ] && [ ! -x "/opt/etc/init.d/S52sing-box" ]; then
    cat << 'EOF_INIT' > /opt/etc/init.d/S99sing-box
#!/bin/sh
ENABLED=yes
PROCS=sing-box
DESC=$PROCS
PATH=/opt/sbin:/opt/bin:/opt/usr/bin:/usr/sbin:/usr/bin:/sbin:/bin
CONF=/opt/etc/sing-box/config.json

start() {
    [ -f "$CONF" ] || exit 1
    echo -n "Starting $DESC... "
    start-stop-daemon -S -b -m -p /opt/var/run/sing-box.pid -x /opt/bin/sing-box -- run -c "$CONF"
    echo "done."
}

stop() {
    echo -n "Stopping $DESC... "
    start-stop-daemon -K -p /opt/var/run/sing-box.pid -s TERM 2>/dev/null
    killall sing-box 2>/dev/null
    rm -f /opt/var/run/sing-box.pid
    echo "done."
}

case "$1" in
    start) start ;;
    stop) stop ;;
    restart) stop; sleep 1; start ;;
    check) /opt/bin/sing-box check -c "$CONF" ;;
    *) echo "Usage: $0 {start|stop|restart|check}"; exit 1 ;;
esac
EOF_INIT
    chmod +x /opt/etc/init.d/S99sing-box
fi

# Перезапуск службы
if [ -x "/opt/etc/init.d/S99sing-box" ]; then
    /opt/etc/init.d/S99sing-box restart >/dev/null 2>&1
elif [ -x "/opt/etc/init.d/S52sing-box" ]; then
    /opt/etc/init.d/S52sing-box restart >/dev/null 2>&1
fi

# 7. Первичное наполнение IP-сетов и запуск netfilter
printf "${YELLOW}[6/6] Инициализация IPSET и применение правил фаервола...${NC}\n"
/opt/scripts/update_ipsets.sh >/dev/null 2>&1 || true
/opt/etc/ndm/netfilter.d/010-proxy.sh >/dev/null 2>&1 || true

printf "\n${GREEN}[OK] Стек прозрачного проксирования успешно развернут!${NC}\n\n"
show_status
exit 0
