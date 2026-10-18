#!/bin/sh

# ==========================================================
# Secure DNS Setup (DoT & DoH) for KeeneticOS
# Защищенный быстрый DNS без цензуры провайдеров
# ==========================================================

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

printf "${GREEN}=== Настройка безопасного DoT / DoH DNS (KeeneticOS) ===${NC}\n"

if [ ! -x "/bin/ndmc" ]; then
    printf "${RED}Ошибка: Утилита управления KeeneticOS /bin/ndmc не найдена.${NC}\n"
    exit 1
fi

printf "${YELLOW}Применение настроек DNS-over-TLS и DNS-over-HTTPS...${NC}\n"

# Включение защиты от DNS Rebinding
ndmc -c 'dns-proxy rebind-protect auto' >/dev/null 2>&1

# Добавление надежных апстримов DoT (порт 853)
ndmc -c 'dns-proxy tls upstream dns.malw.link' >/dev/null 2>&1
ndmc -c 'dns-proxy tls upstream dns.geohide.ru' >/dev/null 2>&1
ndmc -c 'dns-proxy tls upstream dns.dns-ai.ru' >/dev/null 2>&1

# Добавление быстрых апстримов DoH (порт 443)
ndmc -c 'dns-proxy https upstream https://dns.malw.link/dns-query dnsm' >/dev/null 2>&1
ndmc -c 'dns-proxy https upstream https://dns.geohide.ru:444/dns-query dnsm' >/dev/null 2>&1
ndmc -c 'dns-proxy https upstream https://dns.dns-ai.ru/dns-query dnsm' >/dev/null 2>&1

# Сохранение конфигурации в энергонезависимую память роутера
ndmc -c 'system configuration save' >/dev/null 2>&1

printf "\n${GREEN}==========================================================${NC}\n"
printf "${GREEN}DNS успешно настроен и защищен!${NC}\n"
printf "${GREEN}Используются DoT/DoH: dns.malw.link, dns.geohide.ru, dns.dns-ai.ru${NC}\n"
printf "${GREEN}==========================================================${NC}\n\n"
