#!/bin/sh

# ==========================================================
# Module 08: nfqws-menu (Interactive Terminal Management)
# - Official interactive menu by rndnaame for Keenetic/Entware
# - Installs /opt/bin/nfqws-menu with offline & online support
# ==========================================================

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

printf "${GREEN}=== Установка nfqws-menu (Интерактивное терминальное меню) ===${NC}\n"

if [ "$(id -u)" != "0" ]; then
    printf "${RED}Ошибка: Скрипт должен быть запущен с правами root.${NC}\n"
    exit 1
fi

if [ ! -d "/opt" ] || [ ! -x "/opt/bin/opkg" ]; then
    printf "${RED}Ошибка: Среда Entware (/opt) не найдена на этом роутере.${NC}\n"
    exit 1
fi

export PATH="/opt/bin:/opt/sbin:/bin:/sbin:/usr/bin:/usr/sbin"

# 1. Зависимости (whiptail, curl)
if [ ! -x "/opt/bin/whiptail" ] && [ ! -x "/usr/bin/whiptail" ]; then
    printf "${YELLOW}Установка вспомогательного пакета whiptail...${NC}\n"
    opkg update >/dev/null 2>&1 || true
    opkg install whiptail >/dev/null 2>&1 || true
fi

# 2. Поиск локального исходника или загрузка из сети
TARGET="/opt/bin/nfqws-menu"
mkdir -p /opt/bin /opt/sbin

SCRIPT_DIR="$(dirname "$0")"
MENU_URL="https://raw.githubusercontent.com/rndnaame/nfqws-menu/main/nfqws-menu.sh"

INSTALLED=0
if [ -f "$SCRIPT_DIR/../AntiDPI_Toolkit/downloads/nfqws-menu.zip" ]; then
    printf "${CYAN}[LOCAL] Распаковка nfqws-menu из локального архива...${NC}\n"
    unzip -p "$SCRIPT_DIR/../AntiDPI_Toolkit/downloads/nfqws-menu.zip" "nfqws-menu-main/nfqws-menu.sh" > "$TARGET" 2>/dev/null && INSTALLED=1
fi

if [ $INSTALLED -eq 0 ]; then
    printf "${YELLOW}Загрузка nfqws-menu с GitHub...${NC}\n"
    if curl -fsSL --max-time 30 -o "$TARGET" "$MENU_URL"; then
        INSTALLED=1
    fi
fi

if [ $INSTALLED -eq 1 ] && [ -s "$TARGET" ]; then
    chmod 755 "$TARGET"
    ln -sf /opt/bin/nfqws-menu /opt/sbin/nfqws-menu 2>/dev/null || true
    printf "\n${GREEN}[OK] nfqws-menu успешно установлен!${NC}\n"
    printf "Команда для запуска из любого места в терминале: ${YELLOW}nfqws-menu${NC}\n\n"
    exit 0
else
    printf "${RED}[ОШИБКА] Не удалось установить nfqws-menu.${NC}\n"
    exit 1
fi
