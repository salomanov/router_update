#!/bin/sh

# ==========================================================
# Telegram WebSocket Proxy Auto-Installer for Entware
# ==========================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

printf "${GREEN}=== Установка прокси Telegram (tg-ws-proxy) ===${NC}\n"

if [ ! -d "/opt" ] || [ ! -x "/opt/bin/opkg" ]; then
    printf "${RED}Ошибка: Среда Entware (/opt) не найдена на этом роутере.${NC}\n"
    exit 1
fi

export PATH="/opt/bin:/opt/sbin:/bin:/sbin:/usr/bin:/usr/sbin"

# 1. Добавление репозитория feedly
printf "${YELLOW}[1/3] Настройка репозитория feedly...${NC}\n"
mkdir -p /opt/etc/opkg
echo "src/gz feedly_mipsel-3.4 https://spatiumstas.github.io/feedly/mipsel-3.4" > /opt/etc/opkg/feedly.conf

# 2. Установка tg-ws-proxy
printf "${YELLOW}[2/3] Установка tg-ws-proxy через OPKG...${NC}\n"
killall opkg 2>/dev/null
rm -f /opt/tmp/opkg.lock
opkg update >/dev/null 2>&1
opkg install tg-ws-proxy >/dev/null 2>&1

if [ ! -x "/opt/bin/tg-ws-proxy" ]; then
    printf "${RED}Ошибка: Не удалось установить tg-ws-proxy через opkg.${NC}\n"
    exit 1
fi

# 3. Запуск службы
printf "${YELLOW}[3/3] Запуск службы tg-ws-proxy...${NC}\n"
if [ -x "/opt/etc/init.d/S99tg-ws-proxy" ]; then
    /opt/etc/init.d/S99tg-ws-proxy restart
    printf "\n${GREEN}==========================================================${NC}\n"
    printf "${GREEN}tg-ws-proxy успешно установлен и запущен!${NC}\n"
    printf "${GREEN}Порт: 1443${NC}\n"
    printf "${GREEN}Ссылка для подключения отобразится в веб-панели управления.${NC}\n"
    printf "${GREEN}==========================================================${NC}\n\n"
fi
