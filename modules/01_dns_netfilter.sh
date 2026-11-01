#!/bin/sh

# ==========================================================
# Module 01: Secure DNS (DoT / DoH) & NDM Netfilter Network Glue
# - Encrypted DNS upstreams via Keenetic ndnproxy
# - DNS redirect (UDP/TCP 53) to prevent ISP spoofing
# - Instant QUIC (UDP 443) reject to force fast TCP fallback
# - Instant dead IPv6 reject (eliminates Happy Eyeballs timeouts)
# - TCP MSS clamping to PMTU (1360 for L2TP)
# ==========================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

printf "${GREEN}=== [1/5] Настройка защищенного DNS и сетевых правил ===${NC}\n"

if [ "$(id -u)" != "0" ]; then
    printf "${RED}Ошибка: Скрипт должен быть запущен с правами root.${NC}\n"
    exit 1
fi

REPO_RAW="https://raw.githubusercontent.com/salomanov/router_update/main"
CACHE_BUST="?nocache=$(date +%s)$$"

fetch() {
    curl -fsSL --max-time 30 -o "$2" "$1" 2>/dev/null || true
    if [ -s "$2" ]; then
        chmod +x "$2"
        return 0
    fi
    return 1
}

# 1. Настройка шифрованных апстримов DoT и DoH через ndmc
if command -v ndmc >/dev/null 2>&1; then
    printf "${YELLOW}Применение настроек DNS-over-TLS и DNS-over-HTTPS в KeeneticOS...${NC}\n"
    ndmc -c 'dns-proxy rebind-protect auto' >/dev/null 2>&1

    # Надежные апстримы DoT (порт 853)
    ndmc -c 'dns-proxy tls upstream dns.malw.link' >/dev/null 2>&1
    ndmc -c 'dns-proxy tls upstream dns.dns-ai.ru' >/dev/null 2>&1
    ndmc -c 'dns-proxy tls upstream geohide.ru' >/dev/null 2>&1

    # Надежные апстримы DoH (порт 443)
    ndmc -c 'dns-proxy https upstream https://dns.malw.link/dns-query dnsm' >/dev/null 2>&1
    ndmc -c 'dns-proxy https upstream https://dns.dns-ai.ru/dns-query dnsm' >/dev/null 2>&1
    ndmc -c 'dns-proxy https upstream https://geohide.ru/dns-query dnsm' >/dev/null 2>&1

    ndmc -c 'system configuration save' >/dev/null 2>&1
    printf "${GREEN}[OK] DoT и DoH настроены в KeeneticOS.${NC}\n"
fi

# 2. Установка сетевых хуков Keenetic Netfilter
printf "${YELLOW}Установка правил маршрутизации NDM (DNS перехват, QUIC блок, MSS clamp)...${NC}\n"
mkdir -p /opt/etc/ndm/netfilter.d

fetch "${REPO_RAW}/netfilter/005-lan-fix.sh${CACHE_BUST}" /opt/etc/ndm/netfilter.d/005-lan-fix.sh
fetch "${REPO_RAW}/netfilter/015-l2tp.sh${CACHE_BUST}" /opt/etc/ndm/netfilter.d/015-l2tp.sh
fetch "${REPO_RAW}/netfilter/020-block-quic.sh${CACHE_BUST}" /opt/etc/ndm/netfilter.d/020-block-quic.sh

# 3. Активация правил в iptables
[ -x "/opt/etc/ndm/netfilter.d/005-lan-fix.sh" ] && /opt/etc/ndm/netfilter.d/005-lan-fix.sh >/dev/null 2>&1 || true
[ -x "/opt/etc/ndm/netfilter.d/015-l2tp.sh" ] && /opt/etc/ndm/netfilter.d/015-l2tp.sh >/dev/null 2>&1 || true
[ -x "/opt/etc/ndm/netfilter.d/020-block-quic.sh" ] && /opt/etc/ndm/netfilter.d/020-block-quic.sh >/dev/null 2>&1 || true

printf "${GREEN}[OK] Сетевой клей успешно установлен и активирован!${NC}\n\n"
exit 0
