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

run_step() {
    step_num="$1"
    step_name="$2"
    step_url="$3"

    printf "\n${YELLOW}>>> [${step_num}/5] Установка ${step_name}...${NC}\n"
    if curl -fsSL "${step_url}${CACHE_BUST}" | sh; then
        printf "${GREEN}[OK] ${step_name} успешно установлен.${NC}\n"
    else
        printf "${RED}[ОШИБКА] Сбой при установке ${step_name}! Проверьте интернет-соединение.${NC}\n"
    fi
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

printf "\n${GREEN}==========================================================${NC}\n"
printf "${GREEN}      УСТАНОВКА ВСЕХ КОМПОНЕНТОВ ЗАВЕРШЕНА!               ${NC}\n"
printf "${GREEN}==========================================================${NC}\n\n"
printf "👉 Веб-панель GRouter: http://192.168.1.1:8089/\n"
printf "👉 Веб-терминал PuTTY (ttyd): http://192.168.1.1:7681/\n"
printf "👉 Авторизация панели и терминала: admin / Salomanov\n"
printf "👉 Веб-интерфейс nfqws: http://192.168.1.1:90/\n"
printf "👉 YouTube 4K, Instagram и трекеры: активны через nfqws2\n"
printf "👉 Прокси Telegram: запущен на порту 1443\n\n"
