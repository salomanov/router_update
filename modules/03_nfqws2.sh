#!/bin/sh

# ==========================================================
# Module 03: nfqws2 Anti-DPI Engine (Headless / Core)
# - Official nfqws2-keenetic package (without lighttpd/php)
# - Hardened cascade profile (nld=3, clean desync, blobs)
# - S99ytggc (YTGGC_RST instant failover)
# ==========================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

printf "${GREEN}=== Установка nfqws2 Anti-DPI (Основной движок) ===${NC}\n"

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

# 2. Добавление репозитория nfqws2
mkdir -p /opt/etc/opkg
echo "src/gz nfqws2-keenetic https://nfqws.github.io/nfqws2-keenetic/all" > /opt/etc/opkg/nfqws2-keenetic.conf

# 3. Установка пакета nfqws2-keenetic
printf "${YELLOW}Установка пакета nfqws2-keenetic через OPKG...${NC}\n"
if [ -x "/opt/scripts/opkg_update.py" ]; then
    python3 /opt/scripts/opkg_update.py >/dev/null 2>&1 || opkg update >/dev/null 2>&1
else
    opkg update >/dev/null 2>&1
fi
opkg install nfqws2-keenetic >/dev/null 2>&1

if [ ! -x "/opt/usr/bin/nfqws2" ]; then
    printf "${RED}Ошибка: Бинарный файл /opt/usr/bin/nfqws2 не найден после установки.${NC}\n"
    exit 1
fi

# 4. Выбор профиля настроек (Standard vs Hardened)
PROFILE="hardened"
for a in "$@"; do
    case "$a" in
        --standard|--profile=standard) PROFILE="standard" ;;
        --hardened|--profile=hardened) PROFILE="hardened" ;;
    esac
done

REPO_RAW="https://raw.githubusercontent.com/salomanov/router_update/main"
SCRIPT_DIR="$(dirname "$0")"
LOCAL_BASE=""
if [ -d "$SCRIPT_DIR/../configs" ]; then
    LOCAL_BASE="$SCRIPT_DIR/.."
elif [ -d "./configs" ]; then
    LOCAL_BASE="."
elif [ -d "/opt/updates_cache/configs" ]; then
    LOCAL_BASE="/opt/updates_cache"
fi

# Автоопределение активного WAN-интерфейса роутера
DEF_IFACE=$(route -n 2>/dev/null | awk '$1=="0.0.0.0"{print $8; exit}')
[ -z "$DEF_IFACE" ] && DEF_IFACE=$(ip route show default 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="dev") {print $(i+1); exit}}')
[ -z "$DEF_IFACE" ] && DEF_IFACE="ppp0"
printf "Интернет-интерфейс: %s\n" "$DEF_IFACE"

fetch_file() {
    rel_path="$1"
    target="$2"
    if [ -n "$LOCAL_BASE" ] && [ -f "$LOCAL_BASE/$rel_path" ]; then
        cp -f "$LOCAL_BASE/$rel_path" "$target"
        return 0
    fi
    curl -fsSL --max-time 15 -o "$target" "${REPO_RAW}/${rel_path}?$(date +%s)" 2>/dev/null
}

if [ "$PROFILE" = "hardened" ]; then
    printf "${YELLOW}Применение профиля HARDENED (nld=3 + S99ytggc + блобы + QUIC блок)...${NC}\n"
    mkdir -p /opt/etc/nfqws2/blobs /opt/etc/nfqws2/lists /opt/etc/ndm/netfilter.d /opt/etc/init.d

    # 1. nfqws2.conf
    if fetch_file "configs/nfqws2.conf" "/opt/etc/nfqws2/nfqws2.conf"; then
        sed -i -E "s#^ISP_INTERFACE=\".+\"#ISP_INTERFACE=\"$DEF_IFACE\"#" /opt/etc/nfqws2/nfqws2.conf
        printf "  [+] Боевой nfqws2.conf (nld=3) успешно развернут\n"
    fi

    # 2. Бинарные блобы desync
    BLOBS="quic_initial.bin tls_clienthello.bin quic_initial_vk_com.bin tls_clienthello_vk_com.bin quic_initial_rr1---sn-xguxaxjvh-n8me_googlevideo_com_kyber_1.bin tls_clienthello_vk_com_kyber.bin tls_clienthello_ozon_ru.bin tls_clienthello_sberbank_ru.bin tls_clienthello_www_sferum_ru.bin tls_clienthello_ya_ru.bin wireguard_initiation.bin"
    for b in $BLOBS; do
        fetch_file "configs/blobs/$b" "/opt/etc/nfqws2/blobs/$b"
    done
    printf "  [+] Бинарные блобы desync (включая Kyber) синхронизированы\n"

    # 3. Списки доменов
    for lst in user.list exclude.list ipset.list ipset_exclude.list youtube.list; do
        fetch_file "configs/lists/$lst" "/opt/etc/nfqws2/lists/$lst"
    done
    touch /opt/etc/nfqws2/lists/auto.list
    printf "  [+] Списки доменов развернуты\n"

    # 4. Сетевое правило отсечки клиентского QUIC
    if fetch_file "configs/ndm/020-block-quic.sh" "/opt/etc/ndm/netfilter.d/020-block-quic.sh"; then
        chmod +x /opt/etc/ndm/netfilter.d/020-block-quic.sh
        table=filter type=iptables sh /opt/etc/ndm/netfilter.d/020-block-quic.sh 2>/dev/null || true
        printf "  [+] Netfilter 020-block-quic.sh активирован\n"
    fi

    # 5. Демон мгновенного сброса мёртвых GGC IP (S99ytggc)
    fetch_file "configs/ytggc_dead.list" "/opt/etc/ytggc_dead.list"
    if fetch_file "configs/init.d/S99ytggc" "/opt/etc/init.d/S99ytggc"; then
        chmod +x /opt/etc/init.d/S99ytggc
        /opt/etc/init.d/S99ytggc restart >/dev/null 2>&1 || true
        printf "  [+] Служба S99ytggc развернута и активирована\n"
    fi

else
    printf "${GREEN}Применение профиля STANDARD (базовый репозиторный nfqws2)...${NC}\n"
    if [ -f "/opt/etc/nfqws2/nfqws2.conf" ]; then
        sed -i -E "s#^ISP_INTERFACE=\".+\"#ISP_INTERFACE=\"$DEF_IFACE\"#" /opt/etc/nfqws2/nfqws2.conf
    fi
fi

# 6. Запуск nfqws2
if [ -x "/opt/etc/init.d/S51nfqws2" ]; then
    /opt/etc/init.d/S51nfqws2 restart >/dev/null 2>&1
    printf "${GREEN}[OK] nfqws2 успешно запущен (профиль: %s)!${NC}\n\n" "$PROFILE"
fi
exit 0
