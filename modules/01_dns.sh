#!/bin/sh

# ==========================================================
# Module 01: Secure Split DNS (DoT / DoH) for KeeneticOS
# - Bootstrap: 77.88.8.8
# - Global fast DNS: Cloudflare 1.1.1.1 (DoT + DoH)
# - Targeted SmartDNS DoH (cf.dns-ai.ru) for 7 AI domains
# - Cleans legacy broken direct dns.dns-ai.ru / malw / geohide upstreams
# ==========================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

printf "${GREEN}=== Настройка раздельного защищенного DNS (1.1.1.1 + cf.dns-ai.ru) ===${NC}\n"

if [ "$(id -u)" != "0" ]; then
    printf "${RED}Ошибка: Скрипт должен быть запущен с правами root.${NC}\n"
    exit 1
fi

if ! command -v ndmc >/dev/null 2>&1; then
    printf "${RED}Ошибка: Команда ndmc не найдена. Скрипт предназначен для KeeneticOS.${NC}\n"
    exit 1
fi

printf "${YELLOW}Очистка устаревших проблемных апстримов (если есть)...${NC}\n"
ndmc -c 'no dns-proxy tls upstream dns.malw.link' >/dev/null 2>&1 || true
ndmc -c 'no dns-proxy tls upstream dns.dns-ai.ru' >/dev/null 2>&1 || true
ndmc -c 'no dns-proxy tls upstream geohide.ru' >/dev/null 2>&1 || true
ndmc -c 'no dns-proxy tls upstream 194.87.196.13' >/dev/null 2>&1 || true
ndmc -c 'no dns-proxy https upstream https://dns.malw.link/dns-query' >/dev/null 2>&1 || true
ndmc -c 'no dns-proxy https upstream https://dns.dns-ai.ru/dns-query' >/dev/null 2>&1 || true
ndmc -c 'no dns-proxy https upstream https://geohide.ru/dns-query' >/dev/null 2>&1 || true

printf "${YELLOW}Применение эталонной раздельной схемы DNS...${NC}\n"
ndmc -c 'ip name-server 77.88.8.8' >/dev/null 2>&1 || true
ndmc -c 'dns-proxy rebind-protect auto' >/dev/null 2>&1 || true

# Общий быстрый защищенный DNS (Cloudflare DoT + DoH)
ndmc -c 'dns-proxy tls upstream 1.1.1.1 sni cloudflare-dns.com' >/dev/null 2>&1 || true
ndmc -c 'dns-proxy https upstream https://1.1.1.1/dns-query dnsm' >/dev/null 2>&1 || true

# Точечный SmartDNS DoH через Cloudflare Edge только для ИИ-доменов
AI_DNS_DOMAINS="openai.com chatgpt.com oaistatic.com oaiusercontent.com anthropic.com claude.ai gemini.google.com"
for d in $AI_DNS_DOMAINS; do
    ndmc -c "dns-proxy https upstream https://cf.dns-ai.ru/dns-query dnsm domain $d" >/dev/null 2>&1 || true
done

ndmc -c 'system configuration save' >/dev/null 2>&1 || true
printf "${GREEN}[OK] Раздельный DNS (77.88.8.8 + 1.1.1.1 DoT/DoH + cf.dns-ai.ru для 7 ИИ-доменов) настроен и сохранен.${NC}\n\n"
exit 0
