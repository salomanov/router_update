#!/bin/sh

# ==========================================================
# Full Router Setup (Все компоненты одной командой)
# 1. GRouter Control Panel + ttyd (PuTTY веб-терминал)
# 2. nfqws2 Anti-DPI (YouTube 4K, Instagram, Трекеры)
# 3. tg-ws-proxy (Прокси для Telegram)
# 4. Tailscale (VPN Exit Node + удаленный доступ)
# 5. DoT/DoH DNS Resolver
# ==========================================================

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

printf "${CYAN}==========================================================${NC}\n"
printf "${CYAN}      GRouter Full Auto-Setup (Полная установка)         ${NC}\n"
printf "${CYAN}==========================================================${NC}\n\n"

if [ ! -d "/opt" ] || [ ! -x "/opt/bin/opkg" ]; then
    printf "${RED}Ошибка: Среда Entware (/opt) не найдена на этом роутере.${NC}\n"
    printf "Подключите USB-накопитель и включите OPKG в веб-интерфейсе Keenetic.\n"
    exit 1
fi

REPO_RAW="https://raw.githubusercontent.com/salomanov/router_update/main"
CACHE_BUST="?nocache=$(date +%s)$$"
TMP_DIR="/opt/tmp"
mkdir -p "$TMP_DIR"

FAILED=""

run_step() {
    step_num="$1"
    step_name="$2"
    step_url="$3"

    printf "\n${YELLOW}>>> [${step_num}/5] Установка ${step_name}...${NC}\n"

    # Download first, verify, then run. Piping curl into sh hides a failed download:
    # the pipeline status belongs to `sh`, and BusyBox ash has no pipefail.
    step_file="$TMP_DIR/grouter-step-${step_num}.sh"
    if ! curl -fsSL -o "$step_file" "${step_url}${CACHE_BUST}"; then
        printf "${RED}[ОШИБКА] Не удалось скачать ${step_url}${NC}\n"
        FAILED="$FAILED $step_num"
        rm -f "$step_file"
        return 1
    fi
    if [ ! -s "$step_file" ]; then
        printf "${RED}[ОШИБКА] Скачанный скрипт пуст: ${step_url}${NC}\n"
        FAILED="$FAILED $step_num"
        rm -f "$step_file"
        return 1
    fi

    sh "$step_file"
    rc=$?
    rm -f "$step_file"

    if [ $rc -eq 0 ]; then
        printf "${GREEN}[OK] ${step_name} установлен.${NC}\n"
        return 0
    fi

    printf "${RED}[ОШИБКА] Сбой при установке ${step_name} (код ${rc}).${NC}\n"
    FAILED="$FAILED $step_num"
    return 1
}

# 1. Панель управления + ttyd
run_step "1" "GRouter Control Panel & Web-терминал" "${REPO_RAW}/install.sh"

# 2. Обход блокировок nfqws2
run_step "2" "nfqws2 Anti-DPI" "${REPO_RAW}/install_nfqws2.sh"

# 3. Telegram Proxy
run_step "3" "Telegram Proxy (tg-ws-proxy)" "${REPO_RAW}/install_tg_proxy.sh"

# 4. Tailscale VPN
run_step "4" "Tailscale (VPN Exit Node)" "${REPO_RAW}/install_tailscale.sh"

# 5. Защищенный DoT/DoH DNS
run_step "5" "DoT/DoH DNS" "${REPO_RAW}/setup_dns.sh"

LAN_IP=$(ip -4 addr show br0 2>/dev/null | grep -o 'inet [0-9.]*' | awk '{print $2}')
[ -z "$LAN_IP" ] && LAN_IP=$(ip -4 route get 1.1.1.1 2>/dev/null | grep -o 'src [0-9.]*' | awk '{print $2}')
[ -z "$LAN_IP" ] && LAN_IP="192.168.1.1"

if [ -n "$FAILED" ]; then
    printf "\n${RED}==========================================================${NC}\n"
    printf "${RED}      УСТАНОВКА ЗАВЕРШЕНА С ОШИБКАМИ (шаги:${FAILED} )      ${NC}\n"
    printf "${RED}==========================================================${NC}\n\n"
    exit 1
fi

printf "\n${GREEN}==========================================================${NC}\n"
printf "${GREEN}      УСТАНОВКА ВСЕХ КОМПОНЕНТОВ ЗАВЕРШЕНА!               ${NC}\n"
printf "${GREEN}==========================================================${NC}\n\n"
printf "👉 Веб-панель GRouter: http://%s:8089/\n" "$LAN_IP"
printf "👉 Веб-терминал PuTTY (ttyd): http://%s:7681/ (после входа в панель)\n" "$LAN_IP"
printf "👉 Веб-интерфейс nfqws: http://%s:90/\n" "$LAN_IP"
printf "👉 YouTube 4K, Instagram и трекеры: активны через nfqws2\n"
printf "👉 Прокси Telegram: запущен на порту 1443\n\n"
printf "🔑 Вход в панель: admin / Salomanov (стандартный пароль).\n"
printf "   Сменить его можно кнопкой с ключом в шапке панели.\n\n"
