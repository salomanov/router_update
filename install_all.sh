#!/bin/sh

# ==========================================================
# Full Router Setup (Все компоненты одной командой)
# 1. GRouter Control Panel (Веб-панель)
# 2. nfqws2 Anti-DPI (YouTube 4K, Instagram, Трекеры)
# 3. tg-ws-proxy (Прокси для Telegram)
# 4. Tailscale (VPN Exit Node + Удаленный доступ)
# ==========================================================

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

printf "${CYAN}==========================================================${NC}\n"
printf "${CYAN}      GRouter Full Auto-Setup (Полная настройка)         ${NC}\n"
printf "${CYAN}==========================================================${NC}\n\n"

if [ ! -d "/opt" ] || [ ! -x "/opt/bin/opkg" ]; then
    printf "${RED}Ошибка: Среда Entware (/opt) не найдена на этом роутере.${NC}\n"
    printf "Подключите USB-накопитель и включите OPKG в веб-интерфейсе Keenetic.\n"
    exit 1
fi

REPO_RAW="https://raw.githubusercontent.com/salomanov/router_update/main"
CACHE_BUST="?nocache=$(date +%s)$$"

# 1. Панель управления
printf "\n${YELLOW}>>> [1/4] Установка панели управления GRouter...${NC}\n"
curl -sL "${REPO_RAW}/install.sh${CACHE_BUST}" | sh

# 2. Обход блокировок nfqws2
printf "\n${YELLOW}>>> [2/4] Установка nfqws2 (YouTube, Instagram, Трекеры)...${NC}\n"
curl -sL "${REPO_RAW}/install_nfqws2.sh${CACHE_BUST}" | sh

# 3. Telegram Proxy
printf "\n${YELLOW}>>> [3/4] Установка Telegram Proxy (tg-ws-proxy)...${NC}\n"
curl -sL "${REPO_RAW}/install_tg_proxy.sh${CACHE_BUST}" | sh

# 4. Tailscale VPN
printf "\n${YELLOW}>>> [4/4] Установка Tailscale (VPN Exit Node)...${NC}\n"
curl -sL "${REPO_RAW}/install_tailscale.sh${CACHE_BUST}" | sh

printf "\n${GREEN}==========================================================${NC}\n"
printf "${GREEN}      ВСЕ КОМПОНЕНТЫ УСПЕШНО УСТАНОВЛЕНЫ И ЗАПУЩЕНЫ!      ${NC}\n"
printf "${GREEN}==========================================================${NC}\n\n"
printf "👉 Веб-панель управления: http://192.168.1.1:8089/\n"
printf "👉 YouTube 4K, Instagram и трекеры: активны через nfqws2\n"
printf "👉 Прокси Telegram: активен на порту 1443\n"
printf "👉 Для завершения привязки Tailscale перейдите по ссылке выше в консоли.\n\n"
