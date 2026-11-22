#!/bin/sh

# ==========================================================
# GRouter Kit Master Auto-Installer for Keenetic / Entware
# Upstream-First, Granular Modular Architecture
# ==========================================================

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
GRAY='\033[0;37m'
NC='\033[0m'

if [ "$(id -u)" != "0" ]; then
    printf "${RED}Ошибка: Запустите установщик от пользователя root.${NC}\n"
    exit 1
fi

if [ ! -d "/opt" ] || [ ! -x "/opt/bin/opkg" ]; then
    printf "${RED}Ошибка: Среда Entware (/opt) не найдена на этом роутере.${NC}\n"
    printf "Подключите USB-накопитель и включите OPKG в веб-интерфейсе Keenetic.\n"
    exit 1
fi

REPO_RAW="https://raw.githubusercontent.com/salomanov/router_update/main"
CACHE_BUST="?nocache=$(date +%s)$$"
TMP_DIR="/opt/tmp"
SCRIPT_DIR="$(dirname "$0")"
mkdir -p "$TMP_DIR"

run_module() {
    name="$1"
    url="$2"
    base_name="$(basename "$url")"
    file="$TMP_DIR/$base_name"

    printf "\n${YELLOW}>>> Запуск: ${name}...${NC}\n"

    # Проверка локального модуля (поддержка офлайн-установки с флешки/кэша)
    local_mod=""
    if [ -f "$SCRIPT_DIR/modules/$base_name" ]; then
        local_mod="$SCRIPT_DIR/modules/$base_name"
    elif [ -f "./modules/$base_name" ]; then
        local_mod="./modules/$base_name"
    elif [ -f "/opt/updates_cache/modules/$base_name" ]; then
        local_mod="/opt/updates_cache/modules/$base_name"
    fi

    if [ -n "$local_mod" ]; then
        printf "${GREEN}[LOCAL] Исполнение локального модуля: %s${NC}\n" "$local_mod"
        shift 2
        sh "$local_mod" "$@"
        return $?
    fi

    rm -f "$file"
    if ! curl -fsSL --max-time 30 -o "$file" "${url}${CACHE_BUST}"; then
        printf "${RED}[ОШИБКА] Не удалось скачать модуль: ${url}${NC}\n"
        return 1
    fi
    if [ ! -s "$file" ]; then
        printf "${RED}[ОШИБКА] Скачанный файл пуст: ${url}${NC}\n"
        rm -f "$file"
        return 1
    fi

    shift 2
    sh "$file" "$@"
    res=$?
    rm -f "$file"
    return $res
}

# --- Pre-flight Инвентаризация состояния роутера ---
preflight_scan() {
    printf "\n${CYAN}========================================================================${NC}\n"
    printf "${CYAN}             GRouter Kit — Состояние компонентов на роутере            ${NC}\n"
    printf "${CYAN}========================================================================${NC}\n"
    printf "%-22s %-20s %s\n" "КОМПОНЕНТ" "СТАТУС" "ИНФО / ПОРТ"
    printf "%-22s %-20s %s\n" "----------------------" "--------------------" "--------------------"

    # 1. nfqws2
    if [ -x "/opt/usr/bin/nfqws2" ]; then
        PID=$(pgrep -f "/opt/usr/bin/nfqws2" 2>/dev/null | head -n1)
        [ -z "$PID" ] && PID=$(pgrep nfqws 2>/dev/null | head -n1)
        if [ -n "$PID" ]; then
            NLD_STR=$(grep -o 'nld=[0-9]' /opt/etc/nfqws2/nfqws2.conf 2>/dev/null | head -n1)
            [ -n "$NLD_STR" ] && NLD_STR="($NLD_STR)"
            printf "%-22s ${GREEN}%-20s${NC} PID: %s %s\n" "nfqws2 Anti-DPI" "[Установлен, UP]" "$PID" "$NLD_STR"
        else
            printf "%-22s ${YELLOW}%-20s${NC} Служба остановлена\n" "nfqws2 Anti-DPI" "[Установлен, STOP]"
        fi
    else
        printf "%-22s ${GRAY}%-20s${NC} —\n" "nfqws2 Anti-DPI" "[Не установлен]"
    fi

    # 2. nfqws-web
    if [ -f "/opt/share/www/nfqws/index.html" ] || [ -f "/opt/etc/lighttpd/conf.d/80-nfqws.conf" ]; then
        if netstat -tuln 2>/dev/null | grep -q ':90 '; then
            printf "%-22s ${GREEN}%-20s${NC} http://%s:90/\n" "nfqws Веб-панель" "[Установлен, UP]" "$LAN_IP_DETECT"
        else
            printf "%-22s ${YELLOW}%-20s${NC} Порт 90 закрыт\n" "nfqws Веб-панель" "[Установлен, STOP]"
        fi
    else
        printf "%-22s ${GRAY}%-20s${NC} —\n" "nfqws Веб-панель" "[Не установлен]"
    fi

    # 3. nfqws2-ui
    if [ -x "/opt/sbin/nfqws-ui" ] || [ -f "/opt/etc/lighttpd/conf.d/90-nfqws-ui.conf" ]; then
        if netstat -tuln 2>/dev/null | grep -q ':8090 '; then
            printf "%-22s ${GREEN}%-20s${NC} http://%s:8090/\n" "nfqws2-ui Панель" "[Установлен, UP]" "$LAN_IP_DETECT"
        else
            printf "%-22s ${YELLOW}%-20s${NC} Порт 8090 закрыт\n" "nfqws2-ui Панель" "[Установлен, STOP]"
        fi
    else
        printf "%-22s ${GRAY}%-20s${NC} —\n" "nfqws2-ui Панель" "[Не установлен]"
    fi

    # 4. nfqws-menu
    if [ -x "/opt/bin/nfqws-menu" ] || [ -x "/opt/sbin/nfqws-menu" ]; then
        printf "%-22s ${GREEN}%-20s${NC} Команда: nfqws-menu\n" "nfqws-menu CLI" "[Установлен]"
    else
        printf "%-22s ${GRAY}%-20s${NC} —\n" "nfqws-menu CLI" "[Не установлен]"
    fi

    # 5. S99ytggc (GGC Failover)
    if [ -x "/opt/etc/init.d/S99ytggc" ]; then
        GGC_COUNT=$(iptables -S YTGGC_RST 2>/dev/null | grep -c 'REJECT')
        printf "%-22s ${GREEN}%-20s${NC} %s мёртвых узлов в блоке\n" "S99ytggc GGC-сброс" "[Активен]" "$GGC_COUNT"
    else
        printf "%-22s ${GRAY}%-20s${NC} —\n" "S99ytggc GGC-сброс" "[Не установлен]"
    fi

    # 6. Tailscale
    if [ -x "/opt/bin/tailscaled" ]; then
        if pgrep tailscaled >/dev/null 2>&1; then
            TS_IP=$(/opt/bin/tailscale ip -4 2>/dev/null)
            if [ -n "$TS_IP" ]; then
                printf "%-22s ${GREEN}%-20s${NC} IP: %s\n" "Tailscale VPN" "[Установлен, UP]" "$TS_IP"
            else
                printf "%-22s ${YELLOW}%-20s${NC} Требуется авторизация\n" "Tailscale VPN" "[Не авторизован]"
            fi
        else
            printf "%-22s ${YELLOW}%-20s${NC} Служба остановлена\n" "Tailscale VPN" "[Установлен, STOP]"
        fi
    else
        printf "%-22s ${GRAY}%-20s${NC} —\n" "Tailscale VPN" "[Не установлен]"
    fi

    # 7. Telegram WS Proxy
    if [ -x "/opt/bin/tg-ws-proxy" ] || [ -x "/opt/usr/bin/tg-ws-proxy" ]; then
        if pgrep tg-ws-proxy >/dev/null 2>&1; then
            printf "%-22s ${GREEN}%-20s${NC} Порт 1443\n" "Telegram WS-Proxy" "[Установлен, UP]"
        else
            printf "%-22s ${YELLOW}%-20s${NC} Служба остановлена\n" "Telegram WS-Proxy" "[Установлен, STOP]"
        fi
    else
        printf "%-22s ${GRAY}%-20s${NC} —\n" "Telegram WS-Proxy" "[Не установлен]"
    fi

    # 8. Proxy Stack (sing-box / 010-proxy)
    if [ -x "/opt/bin/sing-box" ] || [ -f "/opt/var/run/redsocks.pid" ]; then
        if netstat -tuln 2>/dev/null | grep -q ':10080 '; then
            printf "%-22s ${GREEN}%-20s${NC} :10080 (sing-box -> usque)\n" "Proxy Stack" "[Установлен, UP]"
        elif netstat -tuln 2>/dev/null | grep -q ':12345 '; then
            printf "%-22s ${YELLOW}%-20s${NC} :12345 (redsocks fallback)\n" "Proxy Stack" "[Установлен, UP]"
        else
            printf "%-22s ${YELLOW}%-20s${NC} Порт редиректа закрыт\n" "Proxy Stack" "[Установлен, STOP]"
        fi
    else
        printf "%-22s ${GRAY}%-20s${NC} —\n" "Proxy Stack" "[Не установлен]"
    fi

    # 9. GRouter Панель
    if [ -f "/opt/scripts/router_api.py" ] || [ -f "/opt/bin/router_api.py" ]; then
        if netstat -tuln 2>/dev/null | grep -q ':8089 '; then
            printf "%-22s ${GREEN}%-20s${NC} http://%s:8089/\n" "GRouter Панель" "[Установлен, UP]" "$LAN_IP_DETECT"
        else
            printf "%-22s ${YELLOW}%-20s${NC} Служба остановлена\n" "GRouter Панель" "[Установлен, STOP]"
        fi
    else
        printf "%-22s ${GRAY}%-20s${NC} —\n" "GRouter Панель" "[Не установлен]"
    fi

    printf "${CYAN}========================================================================${NC}\n"
}

# Предварительное определение LAN IP
LAN_IP_DETECT=$(ip -4 addr show br0 2>/dev/null | grep -o 'inet [0-9.]*' | awk '{print $2}')
[ -z "$LAN_IP_DETECT" ] && LAN_IP_DETECT=$(ip -4 addr show br-lan 2>/dev/null | grep -o 'inet [0-9.]*' | awk '{print $2}')
[ -z "$LAN_IP_DETECT" ] && LAN_IP_DETECT=$(ip -4 addr show br1 2>/dev/null | grep -o 'inet [0-9.]*' | awk '{print $2}')
[ -z "$LAN_IP_DETECT" ] && LAN_IP_DETECT=$(ip -4 addr show 2>/dev/null | awk '/inet 192\.168\./{print $2}' | cut -d/ -f1 | head -n1)
[ -z "$LAN_IP_DETECT" ] && LAN_IP_DETECT="192.168.1.1"

# --- Проверка аргументов командной строки ---
DO_DNS=0
DO_GLUE=0
DO_NFQWS=0
DO_NFQWS_WEB=0
DO_NFQWS_UI=0
DO_NFQWS_MENU=0
DO_TG=0
DO_TAILSCALE=0
DO_TAILSCALE_SETUP=0
DO_PROXY=0
DO_PANEL=0
BATCH_MODE=0
DPI_PROFILE="hardened"

for arg in "$@"; do
    case "$arg" in
        --all)
            DO_DNS=1; DO_GLUE=1; DO_NFQWS=1; DO_NFQWS_WEB=1; DO_NFQWS_UI=1; DO_NFQWS_MENU=1; DO_TG=1; DO_TAILSCALE=1; DO_PROXY=1; DO_PANEL=1
            BATCH_MODE=1
            ;;
        --status)
            preflight_scan
            exit 0
            ;;
        --standard|--profile=standard)
            DPI_PROFILE="standard"
            ;;
        --hardened|--profile=hardened)
            DPI_PROFILE="hardened"
            ;;
        --dns)
            DO_DNS=1; BATCH_MODE=1
            ;;
        --netfilter|--glue)
            DO_GLUE=1; BATCH_MODE=1
            ;;
        --nfqws2)
            DO_NFQWS=1; BATCH_MODE=1
            ;;
        --nfqws-web)
            DO_NFQWS_WEB=1; BATCH_MODE=1
            ;;
        --nfqws-ui|--ui)
            DO_NFQWS_UI=1; BATCH_MODE=1
            ;;
        --nfqws-menu|--menu)
            DO_NFQWS_MENU=1; BATCH_MODE=1
            ;;
        --tg)
            DO_TG=1; BATCH_MODE=1
            ;;
        --tailscale)
            DO_TAILSCALE=1; BATCH_MODE=1
            ;;
        --tailscale-setup|--tailscale-login)
            DO_TAILSCALE_SETUP=1; BATCH_MODE=1
            ;;
        --proxy|--sing-box)
            DO_PROXY=1; BATCH_MODE=1
            ;;
        --panel)
            DO_PANEL=1; BATCH_MODE=1
            ;;
        -h|--help)
            printf "Использование: sh install.sh [ОПЦИИ]\n"
            printf "Опции:\n"
            printf "  --status      Показать текущее состояние всех компонентов на роутере\n"
            printf "  --all         Установить все компоненты сразу\n"
            printf "  --dns         Только защищенный DNS (DoT/DoH)\n"
            printf "  --netfilter   Только сетевые правила NDM (DNS 53, QUIC, IPv6, MSS)\n"
            printf "  --nfqws2      Только nfqws2 Anti-DPI (nld=3, S99ytggc, блобы)\n"
            printf "  --nfqws-web   Только официальная веб-панель nfqws (порт 90)\n"
            printf "  --nfqws-ui    Только веб-панель автоподбора nfqws2-ui (порт 8090)\n"
            printf "  --nfqws-menu  Только терминальное меню nfqws-menu\n"
            printf "  --tailscale   Установить Tailscale VPN\n"
            printf "  --tailscale-setup  Запустить мастер авторизации Tailscale (вход по ссылке)\n"
            printf "  --tg          Только Telegram WebSocket прокси (порт 1443)\n"
            printf "  --panel       Только GRouter Панель (порт 8089) и терминал\n"
            printf "Без опций — запуск умного интерактивного меню с аудитом состояния.\n"
            exit 0
            ;;
    esac
done

# Если запрошена только авторизация Tailscale
if [ $DO_TAILSCALE_SETUP -eq 1 ]; then
    if [ -x "/opt/bin/tailscale-login" ]; then
        /opt/bin/tailscale-login
    elif [ -x "/opt/bin/tailscale" ]; then
        /opt/bin/tailscale up --advertise-exit-node --accept-routes --reset
    else
        printf "${RED}Tailscale не установлен. Запустите: sh install.sh --tailscale${NC}\n"
    fi
    exit 0
fi

# --- Интерактивное меню ---
if [ $BATCH_MODE -eq 0 ]; then
    preflight_scan

    printf "  ${GREEN}1)${NC} Умное обновление (Smart Update: обновить nfqws2 + доустановить недостающие компоненты)\n"
    printf "  ${GREEN}2)${NC} Обновить только nfqws2 Anti-DPI (nld=3, S99ytggc, Kyber блобы, списки)\n"
    printf "  ${GREEN}3)${NC} Установить / Обновить nfqws-menu (терминальное интерактивное меню)\n"
    printf "  ${GREEN}4)${NC} Установить / Обновить nfqws2-ui (веб-панель автоподбора :8090)\n"
    printf "  ${GREEN}5)${NC} Настроить и авторизовать Tailscale VPN (вход по ссылке в браузере)\n"
    printf "  ${GREEN}6)${NC} Полная установка всех компонентов (Clean Full Install)\n"
    printf "  ${GREEN}7)${NC} Выборочная установка по компонентам (ручной выбор каждого)\n"
    printf "  ${RED}0)${NC} Выход\n"
    printf "${CYAN}------------------------------------------------------------------------${NC}\n"
    printf "Выберите вариант [1-7, default: 1]: "
    read -r CHOICE

    [ -z "$CHOICE" ] && CHOICE="1"

    case "$CHOICE" in
        1)
            # Smart Update: всегда обновляем AntiDPI и Netfilter
            DO_GLUE=1; DO_NFQWS=1
            [ ! -f "/opt/share/www/nfqws/index.html" ] && DO_NFQWS_WEB=1
            [ ! -x "/opt/bin/nfqws-menu" ] && DO_NFQWS_MENU=1
            [ ! -x "/opt/bin/tg-ws-proxy" ] && DO_TG=1
            [ ! -x "/opt/bin/tailscaled" ] && DO_TAILSCALE=1
            [ ! -f "/opt/etc/ndm/netfilter.d/010-proxy.sh" ] && DO_PROXY=1
            [ ! -f "/opt/scripts/router_api.py" ] && DO_PANEL=1
            ;;
        2)
            DO_GLUE=1; DO_NFQWS=1
            ;;
        3)
            DO_NFQWS_MENU=1
            ;;
        4)
            DO_NFQWS_UI=1
            ;;
        5)
            if [ -x "/opt/bin/tailscale-login" ]; then
                /opt/bin/tailscale-login
                exit 0
            elif [ -x "/opt/bin/tailscale" ]; then
                /opt/bin/tailscale up --advertise-exit-node --accept-routes --reset
                exit 0
            else
                printf "${YELLOW}Tailscale не установлен. Устанавливаем Tailscale...${NC}\n"
                DO_TAILSCALE=1
            fi
            ;;
        6)
            DO_DNS=1; DO_GLUE=1; DO_NFQWS=1; DO_NFQWS_WEB=1; DO_NFQWS_UI=1; DO_NFQWS_MENU=1; DO_TG=1; DO_TAILSCALE=1; DO_PROXY=1; DO_PANEL=1
            ;;
        7)
            printf "\n${YELLOW}--- Настройка компонентов вручную ---${NC}\n"

            printf "1. Настроить защищенный DNS (DoT / DoH апстримы в KeeneticOS)? [y/N]: "
            read -r ANS; [ "$ANS" = "y" ] || [ "$ANS" = "Y" ] && DO_DNS=1

            printf "2. Установить сетевые правила NDM (DNS 53 перехват, блок QUIC, сброс IPv6, MSS)? [Y/n]: "
            read -r ANS; [ -z "$ANS" ] || [ "$ANS" = "y" ] || [ "$ANS" = "Y" ] && DO_GLUE=1

            printf "3. Установить nfqws2 Anti-DPI (nld=3 + S99ytggc + блобы)? [Y/n]: "
            read -r ANS; [ -z "$ANS" ] || [ "$ANS" = "y" ] || [ "$ANS" = "Y" ] && DO_NFQWS=1

            printf "4. Установить официальный веб-интерфейс nfqws (порт 90, lighttpd+php)? [y/N]: "
            read -r ANS; [ "$ANS" = "y" ] || [ "$ANS" = "Y" ] && DO_NFQWS_WEB=1

            printf "5. Установить веб-панель автоподбора nfqws2-ui (порт 8090)? [y/N]: "
            read -r ANS; [ "$ANS" = "y" ] || [ "$ANS" = "Y" ] && DO_NFQWS_UI=1

            printf "6. Установить интерактивное терминальное меню nfqws-menu? [Y/n]: "
            read -r ANS; [ -z "$ANS" ] || [ "$ANS" = "y" ] || [ "$ANS" = "Y" ] && DO_NFQWS_MENU=1

            printf "7. Установить Telegram WebSocket прокси (порт 1443)? [y/N]: "
            read -r ANS; [ "$ANS" = "y" ] || [ "$ANS" = "Y" ] && DO_TG=1

            printf "8. Установить Tailscale VPN? [y/N]: "
            read -r ANS; [ "$ANS" = "y" ] || [ "$ANS" = "Y" ] && DO_TAILSCALE=1

            printf "9. Установить стек проксирования sing-box (:10080) и 010-proxy? [Y/n]: "
            read -r ANS; [ -z "$ANS" ] || [ "$ANS" = "y" ] || [ "$ANS" = "Y" ] && DO_PROXY=1

            printf "10. Установить панель управления GRouter (порт 8089) и веб-терминал? [Y/n]: "
            read -r ANS; [ -z "$ANS" ] || [ "$ANS" = "y" ] || [ "$ANS" = "Y" ] && DO_PANEL=1
            ;;
        0)
            printf "Отмена установки.\n"
            exit 0
            ;;
        *)
            printf "${RED}Неверный выбор. Прерывание.${NC}\n"
            exit 1
            ;;
    esac
fi

# --- Защита памяти MIPS (Swap Guard) ---
SWAP_SIZE=$(free -m 2>/dev/null | awk '/Swap/{print $2}')
[ -z "$SWAP_SIZE" ] && SWAP_SIZE=0
if [ "$SWAP_SIZE" -lt 128 ]; then
    printf "\n${YELLOW}>>> MIPS RAM Guard: Обнаружен дефицит Swap (${SWAP_SIZE} MB). Создаем 512 MB Swap...${NC}\n"
    dd if=/dev/zero of=/opt/swapfile bs=1M count=512 2>/dev/null
    chmod 600 /opt/swapfile
    mkswap /opt/swapfile 2>/dev/null
    swapon /opt/swapfile 2>/dev/null
    cat << 'EOF' > /opt/etc/init.d/S00swap
#!/bin/sh
[ -f /opt/swapfile ] && swapon /opt/swapfile 2>/dev/null
EOF
    chmod +x /opt/etc/init.d/S00swap
    printf "${GREEN}[OK] Swap 512 MB успешно создан и подключен (/opt/swapfile).${NC}\n"
fi

# --- Запуск выбранных модулей ---
ERRORS=0

if [ $DO_DNS -eq 1 ]; then
    run_module "Защищенный DNS (DoT / DoH)" "${REPO_RAW}/modules/01_dns.sh" || ERRORS=$((ERRORS + 1))
fi

if [ $DO_GLUE -eq 1 ]; then
    run_module "Сетевой клей NDM (QUIC, DNS 53, IPv6, MSS)" "${REPO_RAW}/modules/02_netfilter_glue.sh" || ERRORS=$((ERRORS + 1))
fi

if [ $DO_NFQWS -eq 1 ]; then
    run_module "nfqws2 Anti-DPI (${DPI_PROFILE})" "${REPO_RAW}/modules/03_nfqws2.sh" "--${DPI_PROFILE}" || ERRORS=$((ERRORS + 1))
fi

if [ $DO_NFQWS_WEB -eq 1 ]; then
    run_module "Веб-интерфейс nfqws (порт 90)" "${REPO_RAW}/modules/04_nfqws_web.sh" || ERRORS=$((ERRORS + 1))
fi

if [ $DO_NFQWS_UI -eq 1 ]; then
    run_module "nfqws2-ui (Веб-панель :8090)" "${REPO_RAW}/modules/09_nfqws_ui.sh" || ERRORS=$((ERRORS + 1))
fi

if [ $DO_NFQWS_MENU -eq 1 ]; then
    run_module "nfqws-menu (терминальное меню)" "${REPO_RAW}/modules/08_nfqws_menu.sh" || ERRORS=$((ERRORS + 1))
fi

if [ $DO_TG -eq 1 ]; then
    run_module "Telegram Proxy (порт 1443)" "${REPO_RAW}/modules/05_tg_proxy.sh" || ERRORS=$((ERRORS + 1))
fi

if [ $DO_TAILSCALE -eq 1 ]; then
    run_module "Tailscale VPN" "${REPO_RAW}/modules/06_tailscale.sh" || ERRORS=$((ERRORS + 1))
fi

if [ $DO_PROXY -eq 1 ]; then
    run_module "Стек проксирования (sing-box + 010-proxy)" "${REPO_RAW}/modules/10_proxy_stack.sh" || ERRORS=$((ERRORS + 1))
fi

if [ $DO_PANEL -eq 1 ]; then
    run_module "GRouter Панель (8089) и терминал (7681)" "${REPO_RAW}/modules/07_dashboard.sh" || ERRORS=$((ERRORS + 1))
fi

# Определение локального LAN IP роутера (приоритет: локальные мосты br0 / br-lan / br1)
LAN_IP=$(ip -4 addr show br0 2>/dev/null | grep -o 'inet [0-9.]*' | awk '{print $2}')
[ -z "$LAN_IP" ] && LAN_IP=$(ip -4 addr show br-lan 2>/dev/null | grep -o 'inet [0-9.]*' | awk '{print $2}')
[ -z "$LAN_IP" ] && LAN_IP=$(ip -4 addr show br1 2>/dev/null | grep -o 'inet [0-9.]*' | awk '{print $2}')
[ -z "$LAN_IP" ] && LAN_IP=$(ip -4 addr show 2>/dev/null | awk '/inet 192\.168\./{print $2}' | cut -d/ -f1 | head -n1)
[ -z "$LAN_IP" ] && LAN_IP="192.168.1.1"

printf "\n${CYAN}==========================================================${NC}\n"
if [ $ERRORS -eq 0 ]; then
    printf "${GREEN}      УСТАНОВКА ВЫБРАННЫХ КОМПОНЕНТОВ УСПЕШНО ЗАВЕРШЕНА!  ${NC}\n"
else
    printf "${YELLOW}      УСТАНОВКА ЗАВЕРШЕНА С ОШИБКАМИ (ошибок: %d)         ${NC}\n" "$ERRORS"
fi
printf "${CYAN}==========================================================${NC}\n"

[ $DO_PANEL -eq 1 ] && printf "👉 Панель управления: ${GREEN}http://%s:8089/${NC} (admin / Salomanov)\n" "$LAN_IP"
[ $DO_PANEL -eq 1 ] && printf "👉 Веб-терминал PuTTY: ${GREEN}http://%s:7681/${NC} (после входа в панель)\n" "$LAN_IP"
[ $DO_NFQWS_WEB -eq 1 ] && printf "👉 Веб-панель nfqws: ${GREEN}http://%s:90/${NC}\n" "$LAN_IP"
[ $DO_NFQWS_UI -eq 1 ] && printf "👉 Веб-панель автоподбора nfqws2-ui: ${GREEN}http://%s:8090/${NC} (root / пароль роутера)\n" "$LAN_IP"
[ $DO_NFQWS_MENU -eq 1 ] && printf "👉 nfqws-menu: терминальное меню запускается командой ${YELLOW}nfqws-menu${NC}\n"
[ $DO_TG -eq 1 ] && printf "👉 Telegram MTProto прокси: порт 1443 (ссылка: команда ${YELLOW}tg-proxy-link${NC})\n"
[ $DO_TAILSCALE -eq 1 ] && printf "👉 Tailscale: для авторизации выполните ${GREEN}tailscale-login${NC} (статус: ${YELLOW}tailscale-status${NC})\n"
[ $DO_PROXY -eq 1 ] && printf "👉 Стек проксирования: ${GREEN}sing-box :10080 -> usque :8480${NC} (010-proxy.sh + update_ipsets.sh)\n"
printf "\n"
exit $ERRORS
