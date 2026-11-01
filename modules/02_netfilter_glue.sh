#!/bin/sh

# ==========================================================
# Module 02: NDM Netfilter Network Glue for KeeneticOS
# - Redirects LAN port 53 (UDP/TCP) to local resolver
# - Instantly rejects QUIC (UDP 443) to force fast TCP fallback
# - Instantly rejects dead IPv6 to eliminate Happy Eyeballs timeouts
# - Clamps TCP MSS to PMTU (and 1360 on L2TP)
# ==========================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

printf "${GREEN}=== Установка сетевых правил NDM (DNS перехват, QUIC блок, MSS) ===${NC}\n"

if [ "$(id -u)" != "0" ]; then
    printf "${RED}Ошибка: Скрипт должен быть запущен с правами root.${NC}\n"
    exit 1
fi

REPO_RAW="https://raw.githubusercontent.com/salomanov/router_update/main"
CACHE_BUST="?nocache=$(date +%s)$$"
mkdir -p /opt/etc/ndm/netfilter.d

fetch() {
    curl -fsSL --max-time 30 -o "$2" "$1" 2>/dev/null || true
    if [ -s "$2" ]; then
        chmod +x "$2"
        return 0
    fi
    return 1
}

printf "${YELLOW}Загрузка сетевых хуков Keenetic...${NC}\n"
fetch "${REPO_RAW}/netfilter/005-lan-fix.sh${CACHE_BUST}" /opt/etc/ndm/netfilter.d/005-lan-fix.sh
fetch "${REPO_RAW}/netfilter/015-l2tp.sh${CACHE_BUST}" /opt/etc/ndm/netfilter.d/015-l2tp.sh
fetch "${REPO_RAW}/netfilter/020-block-quic.sh${CACHE_BUST}" /opt/etc/ndm/netfilter.d/020-block-quic.sh

# Активация правил в iptables
[ -x "/opt/etc/ndm/netfilter.d/005-lan-fix.sh" ] && /opt/etc/ndm/netfilter.d/005-lan-fix.sh >/dev/null 2>&1 || true
[ -x "/opt/etc/ndm/netfilter.d/015-l2tp.sh" ] && /opt/etc/ndm/netfilter.d/015-l2tp.sh >/dev/null 2>&1 || true
[ -x "/opt/etc/ndm/netfilter.d/020-block-quic.sh" ] && /opt/etc/ndm/netfilter.d/020-block-quic.sh >/dev/null 2>&1 || true

printf "${GREEN}[OK] Сетевой клей успешно установлен и активирован!${NC}\n\n"
exit 0
