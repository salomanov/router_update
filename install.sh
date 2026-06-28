#!/bin/sh

# ==================================================
# GRouter Control Panel Auto-Installer for Entware
# ==================================================

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

printf "${GREEN}Начинаю установку GRouter Control Panel...${NC}\n"

# 0. Проверка среды Entware
if [ ! -d "/opt" ] || [ ! -x "/opt/bin/opkg" ]; then
    printf "${RED}Ошибка: Среда Entware не найдена на этом роутере. Установка невозможна.${NC}\n"
    exit 1
fi

# 1. Предварительная остановка старой версии сервиса (если запущен)
API_PIDFILE="/opt/var/run/router-api.pid"
INIT_SCRIPT="/opt/etc/init.d/S90router-api"

if [ -f "$API_PIDFILE" ]; then
    OLD_PID=$(cat "$API_PIDFILE" 2>/dev/null)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        printf "Обнаружен запущенный сервис Router API (PID %s). Останавливаю...\n" "$OLD_PID"
        if [ -x "$INIT_SCRIPT" ]; then
            "$INIT_SCRIPT" stop > /dev/null 2>&1
        else
            kill "$OLD_PID" 2>/dev/null
        fi
        sleep 2
        if kill -0 "$OLD_PID" 2>/dev/null; then
            kill -9 "$OLD_PID" 2>/dev/null
        fi
        rm -f "$API_PIDFILE"
        printf "Старая версия остановлена.\n"
    else
        rm -f "$API_PIDFILE"
    fi
fi

# 2. Проверка и установка системных зависимостей
DEPS="python3-light python3-logging curl"
NEED_UPDATE=0

printf "Проверка зависимостей...\n"
for pkg in $DEPS; do
    if ! opkg list-installed | grep -q "^${pkg} -"; then
        printf "Пакет %s не найден. Требуется установка.\n" "$pkg"
        NEED_UPDATE=1
    fi
done

if [ "$NEED_UPDATE" -eq 1 ]; then
    printf "Обновление списков пакетов OPKG...\n"
    opkg update > /dev/null
    printf "Установка недостающих пакетов...\n"
    opkg install $DEPS > /dev/null
    if [ $? -ne 0 ]; then
        printf "${RED}Ошибка при установке системных пакетов.${NC}\n"
        exit 1
    fi
    printf "Зависимости установлены.\n"
fi

# 3. Создание папок
printf "Создание каталогов...\n"
mkdir -p /opt/scripts
mkdir -p /opt/etc/init.d
mkdir -p /opt/share/router-control-center

# 4. Загрузка исходных файлов с репозитория GitHub
REPO_RAW="https://raw.githubusercontent.com/salomanov/router_update/main"

printf "Загрузка бэкенда и скрипта инициализации...\n"
curl -sL -o /opt/scripts/router_api.py "${REPO_RAW}/router_api.py"
if [ $? -ne 0 ]; then
    printf "${RED}Ошибка при скачивании бэкенда.${NC}\n"
    exit 1
fi

curl -sL -o /opt/etc/init.d/S90router-api "${REPO_RAW}/S90router-api"
if [ $? -ne 0 ]; then
    printf "${RED}Ошибка при скачивании init-скрипта.${NC}\n"
    exit 1
fi

printf "Загрузка статических веб-файлов...\n"
curl -sL -o /opt/share/router-control-center/index.html "${REPO_RAW}/index.html"
curl -sL -o /opt/share/router-control-center/style.css "${REPO_RAW}/style.css"
curl -sL -o /opt/share/router-control-center/app.js "${REPO_RAW}/app.js"
if [ $? -ne 0 ]; then
    printf "${RED}Ошибка при скачивании статических веб-файлов.${NC}\n"
    exit 1
fi

# 5. Права на запуск
chmod 755 /opt/scripts/router_api.py
chmod 755 /opt/etc/init.d/S90router-api

# 6. Запуск
printf "Запуск Router API...\n"
/opt/etc/init.d/S90router-api start

printf "${GREEN}Установка успешно завершена!${NC}\n"
printf "Панель управления доступна по локальному адресу:\n"
printf "👉 ${GREEN}http://192.168.1.1:8089/${NC}\n"
