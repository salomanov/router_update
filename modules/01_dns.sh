#!/bin/sh

# ==========================================================
# Module 01: Secure DNS (DoT / DoH) for KeeneticOS
# - Encrypted DNS upstreams via Keenetic ndnproxy
# - Automatic Rebind Protection
# ==========================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

printf "${GREEN}=== Настройка защищенного DNS (DoT / DoH) ===${NC}\n"

if [ "$(id -u)" != "0" ]; then
    printf "${RED}Ошибка: Скрипт должен быть запущен с правами root.${NC}\n"
    exit 1
fi

if ! command -v ndmc >/dev/null 2>&1; then
    printf "${RED}Ошибка: Команда ndmc не найдена. Скрипт предназначен для KeeneticOS.${NC}\n"
    exit 1
fi

printf "${YELLOW}Применение настроек DNS-over-TLS и DNS-over-HTTPS...${NC}\n"
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
printf "${GREEN}[OK] DoT и DoH успешно настроены в KeeneticOS.${NC}\n\n"
exit 0
