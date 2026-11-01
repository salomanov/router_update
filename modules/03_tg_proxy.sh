#!/bin/sh

# ==========================================================
# Module 03: Telegram MTProto WebSocket Proxy (Port 1443)
# ==========================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

printf "${GREEN}=== [3/5] Установка Telegram Proxy (tg-ws-proxy) ===${NC}\n"

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
printf "${YELLOW}Настройка репозитория feedly...${NC}\n"
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

# 4. Запуск службы
if [ -x "/opt/etc/init.d/S99tg-ws-proxy" ]; then
    /opt/etc/init.d/S99tg-ws-proxy restart >/dev/null 2>&1
    printf "${GREEN}[OK] tg-ws-proxy запущен на порту 1443.${NC}\n\n"
fi
exit 0
