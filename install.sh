#!/bin/sh

# ==========================================================
# GRouter Kit Master Auto-Installer for Keenetic / Entware
# Upstream-First, Modular Architecture
# ==========================================================

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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
mkdir -p "$TMP_DIR"

run_module() {
    name="$1"
    url="$2"
    file="$TMP_DIR/$(basename "$url")"

    printf "\n${YELLOW}>>> Запуск: ${name}...${NC}\n"
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

    sh "$file"
    res=$?
    rm -f "$file"
    return $res
}

# --- Проверка аргументов командной строки ---
DO_DNS=0
DO_NFQWS=0
DO_TG=0
DO_TAILSCALE=0
DO_PANEL=0
BATCH_MODE=0

for arg in "$@"; do
    case "$arg" in
        --all)
            DO_DNS=1; DO_NFQWS=1; DO_TG=1; DO_TAILSCALE=1; DO_PANEL=1; BATCH_MODE=1
            ;;
        --dns)
            DO_DNS=1; BATCH_MODE=1
            ;;
        --nfqws2)
            DO_NFQWS=1; BATCH_MODE=1
            ;;
        --tg)
            DO_TG=1; BATCH_MODE=1
            ;;
        --tailscale)
            DO_TAILSCALE=1; BATCH_MODE=1
            ;;
        --panel)
            DO_PANEL=1; BATCH_MODE=1
            ;;
        -h|--help)
            printf "Использование: sh install.sh [ОПЦИИ]\n"
            printf "Опции:\n"
            printf "  --all        Установить все компоненты сразу\n"
            printf "  --dns        Только защищенный DNS и сетевые правила NDM\n"
            printf "  --nfqws2     Только nfqws2 Anti-DPI + Web UI (порт 90)\n"
            printf "  --tg         Только Telegram WebSocket прокси (порт 1443)\n"
            printf "  --tailscale  Только Tailscale VPN\n"
            printf "  --panel      Только GRouter Панель (порт 8089) и терминал\n"
            printf "Без опций — интерактивное меню выбора.\n"
            exit 0
            ;;
    esac
done

# --- Интерактивное меню ---
if [ $BATCH_MODE -eq 0 ]; then
    printf "${CYAN}==========================================================${NC}\n"
    printf "${CYAN}             GRouter Kit — Меню Установки                 ${NC}\n"
    printf "${CYAN}==========================================================${NC}\n"
    printf "  ${GREEN}1)${NC} Полная установка (Рекомендуется — всё включено)\n"
    printf "  ${GREEN}2)${NC} Выборочная установка (выбрать нужные компоненты)\n"
    printf "  ${GREEN}3)${NC} Только сетевой клей и защищенный DNS (DoH/DoT, QUIC/MSS fix)\n"
    printf "  ${GREEN}4)${NC} Только nfqws2 Anti-DPI + Web UI (порт 90)\n"
    printf "  ${GREEN}5)${NC} Только панель управления GRouter (порт 8089) и терминал\n"
    printf "  ${RED}0)${NC} Выход\n"
    printf "${CYAN}----------------------------------------------------------${NC}\n"
    printf "Выберите вариант [1-5, default: 1]: "
    read -r CHOICE

    [ -z "$CHOICE" ] && CHOICE="1"

    case "$CHOICE" in
        1)
            DO_DNS=1; DO_NFQWS=1; DO_TG=1; DO_TAILSCALE=1; DO_PANEL=1
            ;;
        2)
            printf "\n${YELLOW}--- Настройка компонентов ---${NC}\n"
            
            printf "1. Настроить защищенный DNS (DoT/DoH) и NDM-клей (блок QUIC, сброс IPv6, MSS)? [Y/n]: "
            read -r ANS; [ -z "$ANS" ] || [ "$ANS" = "y" ] || [ "$ANS" = "Y" ] && DO_DNS=1

            printf "2. Установить nfqws2 Anti-DPI + Web UI (порт 90)? [Y/n]: "
            read -r ANS; [ -z "$ANS" ] || [ "$ANS" = "y" ] || [ "$ANS" = "Y" ] && DO_NFQWS=1

            printf "3. Установить Telegram WebSocket прокси (порт 1443)? [y/N]: "
            read -r ANS; [ "$ANS" = "y" ] || [ "$ANS" = "Y" ] && DO_TG=1

            printf "4. Установить Tailscale VPN? [y/N]: "
            read -r ANS; [ "$ANS" = "y" ] || [ "$ANS" = "Y" ] && DO_TAILSCALE=1

            printf "5. Установить панель управления GRouter (порт 8089) и веб-терминал? [Y/n]: "
            read -r ANS; [ -z "$ANS" ] || [ "$ANS" = "y" ] || [ "$ANS" = "Y" ] && DO_PANEL=1
            ;;
        3)
            DO_DNS=1
            ;;
        4)
            DO_NFQWS=1
            ;;
        5)
            DO_PANEL=1
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

# --- Запуск выбранных модулей по оптимальному порядку ---
ERRORS=0

if [ $DO_DNS -eq 1 ]; then
    run_module "Защищенный DNS и сетевой клей" "${REPO_RAW}/modules/01_dns_netfilter.sh" || ERRORS=$((ERRORS + 1))
fi

if [ $DO_NFQWS -eq 1 ]; then
    run_module "nfqws2 Anti-DPI и Web UI (порт 90)" "${REPO_RAW}/modules/02_nfqws2.sh" || ERRORS=$((ERRORS + 1))
fi

if [ $DO_TG -eq 1 ]; then
    run_module "Telegram Proxy (порт 1443)" "${REPO_RAW}/modules/03_tg_proxy.sh" || ERRORS=$((ERRORS + 1))
fi

if [ $DO_TAILSCALE -eq 1 ]; then
    run_module "Tailscale VPN" "${REPO_RAW}/modules/04_tailscale.sh" || ERRORS=$((ERRORS + 1))
fi

if [ $DO_PANEL -eq 1 ]; then
    run_module "GRouter Панель и Web-терминал" "${REPO_RAW}/modules/05_dashboard.sh" || ERRORS=$((ERRORS + 1))
fi

LAN_IP=$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}')
[ -z "$LAN_IP" ] && LAN_IP=$(ip -4 addr show br0 2>/dev/null | grep -o 'inet [0-9.]*' | awk '{print $2}')
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
[ $DO_NFQWS -eq 1 ] && printf "👉 Веб-панель nfqws: ${GREEN}http://%s:90/${NC}\n" "$LAN_IP"
[ $DO_TG -eq 1 ] && printf "👉 Telegram MTProto прокси: порт 1443\n"
[ $DO_TAILSCALE -eq 1 ] && printf "👉 Tailscale: /opt/bin/tailscale up\n"
printf "\n"
exit $ERRORS
