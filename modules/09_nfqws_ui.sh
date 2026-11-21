#!/bin/sh

# ==========================================================
# Module 09: nfqws2-ui (Web Interface by zemidala)
# - Modern Web UI for nfqws2 with automated strategy selector
# - Runs on isolated port :8090 via lighttpd virtual socket
# - Safe co-existence with nfqws-keenetic-web on port :90
# - Offline & Online hybrid installer support
# ==========================================================

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
GRAY='\033[0;37m'
NC='\033[0m'

if [ "$(id -u)" != "0" ]; then
    printf "${RED}Ошибка: Скрипт должен быть запущен с правами root.${NC}\n"
    exit 1
fi

if [ ! -d "/opt" ] || [ ! -x "/opt/bin/opkg" ]; then
    printf "${RED}Ошибка: Среда Entware (/opt) не найдена на этом роутере.${NC}\n"
    exit 1
fi

export PATH="/opt/sbin:/opt/bin:/opt/usr/sbin:/opt/usr/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Определение локального LAN IP роутера
LAN_IP=$(ip -4 addr show br0 2>/dev/null | grep -o 'inet [0-9.]*' | awk '{print $2}')
[ -z "$LAN_IP" ] && LAN_IP=$(ip -4 addr show br-lan 2>/dev/null | grep -o 'inet [0-9.]*' | awk '{print $2}')
[ -z "$LAN_IP" ] && LAN_IP=$(ip -4 addr show br1 2>/dev/null | grep -o 'inet [0-9.]*' | awk '{print $2}')
[ -z "$LAN_IP" ] && LAN_IP=$(ip -4 addr show 2>/dev/null | grep -o 'inet 192\.168\.[0-9.]*' | awk '{print $2}' | head -n1)
[ -z "$LAN_IP" ] && LAN_IP="192.168.1.1"

show_status() {
    printf "${CYAN}=== Статус nfqws2-ui (Веб-панель :8090) ===${NC}\n"
    if [ -x "/opt/sbin/nfqws-ui" ] || [ -f "/opt/etc/lighttpd/conf.d/90-nfqws-ui.conf" ]; then
        VER=$(opkg list-installed nfqws2-ui 2>/dev/null | awk '{print $3}')
        [ -z "$VER" ] && VER="установлен"
        if netstat -tuln 2>/dev/null | grep -q ':8090 '; then
            printf "Статус: ${GREEN}[UP] Активен и слушает порт 8090${NC} (версия: %s)\n" "$VER"
            printf "Адрес:  ${GREEN}http://%s:8090/${NC} (логин: root / пароль от роутера)\n" "$LAN_IP"
        else
            printf "Статус: ${YELLOW}[STOP] Установлен, но порт 8090 не активен${NC}\n"
            printf "Попробуйте перезапустить lighttpd: /opt/etc/init.d/S80lighttpd restart\n"
        fi
    else
        printf "Статус: ${GRAY}[НЕ УСТАНОВЛЕН]${NC}\n"
    fi
}

uninstall_ui() {
    printf "${YELLOW}Удаление nfqws2-ui (порт 8090)...${NC}\n"
    rm -f /opt/etc/lighttpd/conf.d/90-nfqws-ui.conf 2>/dev/null
    rm -rf /opt/share/www/nfqws-ui /opt/etc/nfqws-ui 2>/dev/null
    opkg remove nfqws2-ui >/dev/null 2>&1 || true
    
    if [ -x "/opt/etc/init.d/S80lighttpd" ]; then
        /opt/etc/init.d/S80lighttpd restart >/dev/null 2>&1 || true
    fi
    printf "${GREEN}[OK] nfqws2-ui успешно удален. Порт 90 и nfqws2 остались нетронутыми.${NC}\n"
    exit 0
}

# Обработка аргументов
case "$1" in
    --status)
        show_status
        exit 0
        ;;
    --uninstall|--remove)
        uninstall_ui
        ;;
esac

printf "${GREEN}=== Установка nfqws2-ui (Веб-панель на порту 8090) ===${NC}\n"

# 1. Проверка ядра nfqws2
if [ ! -x "/opt/usr/bin/nfqws2" ]; then
    printf "${YELLOW}[!] Предупреждение: nfqws2 Anti-DPI не обнаружен. Устанавливаем базовый nfqws2...${NC}\n"
    SCRIPT_DIR="$(dirname "$0")"
    if [ -f "$SCRIPT_DIR/03_nfqws2.sh" ]; then
        sh "$SCRIPT_DIR/03_nfqws2.sh"
    fi
fi

# 2. Проверка и установка зависимостей lighttpd и PHP
printf "${YELLOW}Проверка зависимостей (lighttpd, mod-cgi, php8-cgi)...${NC}\n"
DEPS_NEEDED=""
for pkg in lighttpd lighttpd-mod-cgi lighttpd-mod-rewrite lighttpd-mod-setenv php8-cgi php8-mod-session php8-mod-curl cron; do
    if ! opkg list-installed "$pkg" 2>/dev/null | grep -q "$pkg"; then
        DEPS_NEEDED="$DEPS_NEEDED $pkg"
    fi
done

if [ -n "$DEPS_NEEDED" ]; then
    printf "${CYAN}Доустановка недостающих пакетов:%s...${NC}\n" "$DEPS_NEEDED"
    opkg update >/dev/null 2>&1 || true
    opkg install $DEPS_NEEDED >/dev/null 2>&1 || true
fi

# 3. Поиск пакета nfqws2-ui (офлайн / локальный кэш / сеть)
SCRIPT_DIR="$(dirname "$0")"
IPK_TARGET="/opt/tmp/nfqws2-ui.ipk"
INSTALLED=0

# Проверка локальных путей к пакету
LOCAL_IPK=""
if [ -f "$SCRIPT_DIR/../packages/nfqws2-ui_1.34.2-1_all_entware.ipk" ]; then
    LOCAL_IPK="$SCRIPT_DIR/../packages/nfqws2-ui_1.34.2-1_all_entware.ipk"
elif [ -f "/opt/updates_cache/packages/nfqws2-ui_1.34.2-1_all_entware.ipk" ]; then
    LOCAL_IPK="/opt/updates_cache/packages/nfqws2-ui_1.34.2-1_all_entware.ipk"
elif [ -f "/opt/tmp/nfqws2-ui_1.34.2-1_all_entware.ipk" ]; then
    LOCAL_IPK="/opt/tmp/nfqws2-ui_1.34.2-1_all_entware.ipk"
fi

if [ -n "$LOCAL_IPK" ]; then
    printf "${GREEN}[LOCAL] Установка nfqws2-ui из локального пакета: %s${NC}\n" "$LOCAL_IPK"
    if opkg install "$LOCAL_IPK"; then
        INSTALLED=1
    fi
fi

# Если локальный пакет не найден или не встал, пробуем онлайн-установку
if [ $INSTALLED -eq 0 ]; then
    printf "${CYAN}[ONLINE] Загрузка nfqws2-ui из официального репозитория zemidala/nfqws2-ui...${NC}\n"
    RELEASE_URL="https://github.com/zemidala/nfqws2-ui/releases/latest/download/install.sh"
    if curl -fsSL --connect-timeout 10 --max-time 60 -o /opt/tmp/zemidala_install.sh "$RELEASE_URL"; then
        sh /opt/tmp/zemidala_install.sh
        INSTALLED=$?
        rm -f /opt/tmp/zemidala_install.sh
    fi
fi

# 4. Проверка и изоляция виртуального сокета lighttpd на :8090
CONF_90="/opt/etc/lighttpd/conf.d/90-nfqws-ui.conf"
if [ ! -f "$CONF_90" ] || ! grep -q 'socket.*8090' "$CONF_90" 2>/dev/null; then
    printf "${YELLOW}Создание изолированной конфигурации lighttpd для порта :8090...${NC}\n"
    mkdir -p /opt/etc/lighttpd/conf.d
    cat << 'EOFCONF' > "$CONF_90"
# nfqws2-ui virtual socket configuration
$SERVER["socket"] == ":8090" {
    cgi.assign += ( ".php" => "/opt/bin/php-cgi" )
    static-file.exclude-extensions += ( ".php" )
    setenv.set-environment = ( "PATH" => "/opt/sbin:/opt/bin:/opt/usr/sbin:/opt/usr/bin:/usr/sbin:/usr/bin:/sbin:/bin" )
    index-file.names = ( "index.html" )
    server.error-handler-404 = "/nfqws-ui/index.html"
    url.rewrite-once = ( "^/(.*)" => "/nfqws-ui/$1" )
}
EOFCONF
fi

# 5. Перезапуск веб-сервера lighttpd
if [ -x "/opt/etc/init.d/S80lighttpd" ]; then
    printf "Перезапуск веб-сервера lighttpd...\n"
    /opt/etc/init.d/S80lighttpd restart >/dev/null 2>&1 || true
    sleep 2
fi

# 6. Финальная проверка
if netstat -tuln 2>/dev/null | grep -q ':8090 '; then
    printf "\n${GREEN}[OK] nfqws2-ui успешно развёрнут и активен!${NC}\n"
    printf "👉 Панель автоподбора: ${GREEN}http://%s:8090/${NC}\n" "$LAN_IP"
    printf "Вход: логин ${YELLOW}root${NC}, пароль — пароль администратора роутера.\n\n"
    exit 0
else
    printf "\n${YELLOW}[!] Пакет установлен, но порт 8090 пока не отвечает.${NC}\n"
    printf "Проверьте журнал: /opt/etc/init.d/S80lighttpd check\n\n"
    exit 0
fi
