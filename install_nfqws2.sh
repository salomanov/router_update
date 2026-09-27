#!/bin/sh

# ==========================================================
# nfqws2 Anti-DPI Auto-Installer for Keenetic / Entware
# YouTube 4K, Instagram, NNM-Club, Rutracker, Discord, BambuLab
# ==========================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

printf "${GREEN}=== Установка обхода блокировок (nfqws2) ===${NC}\n"

# 1. Проверка Entware
if [ ! -d "/opt" ] || [ ! -x "/opt/bin/opkg" ]; then
    printf "${RED}Ошибка: Среда Entware (/opt) не найдена на этом роутере.${NC}\n"
    exit 1
fi

export PATH="/opt/bin:/opt/sbin:/bin:/sbin:/usr/bin:/usr/sbin"

# 2. Добавление репозитория nfqws2
printf "${YELLOW}[1/4] Настройка репозитория nfqws2...${NC}\n"
mkdir -p /opt/etc/opkg
echo "src/gz nfqws2-keenetic https://nfqws.github.io/nfqws2-keenetic/all" > /opt/etc/opkg/nfqws2-keenetic.conf

# 3. Установка пакета
printf "${YELLOW}[2/4] Установка пакета nfqws2-keenetic через OPKG...${NC}\n"
killall opkg 2>/dev/null
rm -f /opt/tmp/opkg.lock
opkg update >/dev/null 2>&1
opkg install nfqws2-keenetic >/dev/null 2>&1

if [ ! -x "/opt/usr/bin/nfqws2" ]; then
    printf "${RED}Ошибка: Не удалось установить nfqws2-keenetic через opkg.${NC}\n"
    exit 1
fi

# 4. Загрузка готовой конфигурации, списков и бинарных блобов
printf "${YELLOW}[3/4] Загрузка проверенной конфигурации и списков хостов...${NC}\n"
mkdir -p /opt/etc/nfqws2/lists /opt/etc/nfqws2/blobs /opt/etc/nfqws2/lua

REPO_RAW="https://raw.githubusercontent.com/salomanov/router_update/main/configs"
CACHE_BUST="?nocache=$(date +%s)$$"

# Скачивание nfqws2.conf
curl -sL -o /opt/etc/nfqws2/nfqws2.conf "${REPO_RAW}/nfqws2.conf${CACHE_BUST}"

# Скачивание списков
curl -sL -o /opt/etc/nfqws2/lists/user.list "${REPO_RAW}/lists/user.list${CACHE_BUST}"
curl -sL -o /opt/etc/nfqws2/lists/exclude.list "${REPO_RAW}/lists/exclude.list${CACHE_BUST}"
curl -sL -o /opt/etc/nfqws2/lists/ipset.list "${REPO_RAW}/lists/ipset.list${CACHE_BUST}"
curl -sL -o /opt/etc/nfqws2/lists/ipset_exclude.list "${REPO_RAW}/lists/ipset_exclude.list${CACHE_BUST}"
touch /opt/etc/nfqws2/lists/auto.list

# Скачивание бинарных блобов для desync
BLOBS="ACTIVE_DISCORD_UDP.bin discord_udp.bin quic_initial.bin quic_initial_dbankcloud_ru.bin quic_initial_vk_com.bin quic_initial_www_google_com.bin stun.bin tls_clienthello.bin tls_clienthello_4pda_to.bin tls_clienthello_max_ru.bin tls_clienthello_vk_com.bin tls_clienthello_www_google_com.bin"
for b in $BLOBS; do
    curl -sL -o "/opt/etc/nfqws2/blobs/$b" "${REPO_RAW}/blobs/$b${CACHE_BUST}"
done

# Настройка блокировки QUIC (UDP 443) для исключения заиканий звука и видео в YouTube
mkdir -p /opt/etc/ndm/netfilter.d
curl -sL -o /opt/etc/ndm/netfilter.d/020-block-quic.sh "${REPO_RAW}/ndm/020-block-quic.sh${CACHE_BUST}"
chmod +x /opt/etc/ndm/netfilter.d/020-block-quic.sh
/opt/etc/ndm/netfilter.d/020-block-quic.sh >/dev/null 2>&1

# 5. Запуск и проверка службы
printf "${YELLOW}[4/4] Запуск службы nfqws2...${NC}\n"
if [ -x "/opt/etc/init.d/S51nfqws2" ]; then
    /opt/etc/init.d/S51nfqws2 restart >/dev/null 2>&1
    sleep 2
    if pgrep nfqws2 >/dev/null; then
        printf "\n${GREEN}==========================================================${NC}\n"
        printf "${GREEN}nfqws2 успешно установлен и запущен!${NC}\n"
        printf "${GREEN}YouTube, Instagram, Rutracker, NNM-Club и Discord активны.${NC}\n"
        printf "${GREEN}==========================================================${NC}\n\n"
    else
        printf "${RED}Внимание: Служба nfqws2 не запустилась, проверьте /opt/var/log/nfqws2.log${NC}\n"
    fi
fi
