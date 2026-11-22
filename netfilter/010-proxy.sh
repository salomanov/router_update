#!/bin/sh
# RouterKit Universal Core: Unified Netfilter Proxy Dispatcher
# Reference: Router_Workspace/etalon/netfilter/010-proxy.sh
# 
# Works only during NAT table processing in KeeneticOS NDM netfilter hooks
[ "$table" != "nat" ] && exit 0

LOCKDIR="/tmp/rk_proxy_dispatch.lock"
if ! mkdir "$LOCKDIR" 2>/dev/null; then
    exit 0
fi
trap 'rm -rf "$LOCKDIR"' EXIT

CHAIN="REDSOCKS_TG"
PIDFILE="/opt/var/run/redsocks.pid"
IPT="iptables -t nat"

clean_rules() {
    $IPT -D PREROUTING -p tcp -j "$CHAIN" 2>/dev/null
    $IPT -D OUTPUT -p tcp -j "$CHAIN" 2>/dev/null
    $IPT -F "$CHAIN" 2>/dev/null
    $IPT -X "$CHAIN" 2>/dev/null
}

# 1. Проверяем наличие активного прокси-демона (sing-box приоритетен, redsocks как фолбэк)
if pidof sing-box >/dev/null 2>&1; then
    PROXY_PORT=10080
elif [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    PROXY_PORT=12345
else
    clean_rules
    exit 0
fi

# 2. Гарантируем наличие базовых ipset
ipset create META_NETS hash:net -exist
ipset create AI_NETS hash:ip -exist

# 3. Инициализация цепочки
$IPT -N "$CHAIN" 2>/dev/null
$IPT -F "$CHAIN"

# 4. Защита локальных сетей и самого роутера (Zero interference с локальными портами)
$IPT -A "$CHAIN" -d 127.0.0.0/8 -j RETURN
$IPT -A "$CHAIN" -d 192.168.0.0/16 -j RETURN
$IPT -A "$CHAIN" -d 10.0.0.0/8 -j RETURN
$IPT -A "$CHAIN" -d 172.16.0.0/12 -j RETURN
$IPT -A "$CHAIN" -d 224.0.0.0/4 -j RETURN

# Исключаем системные DNS Keenetic
$IPT -A "$CHAIN" -d 77.88.8.8 -j RETURN
$IPT -A "$CHAIN" -d 1.1.1.1 -j RETURN
$IPT -A "$CHAIN" -d 8.8.8.8 -j RETURN

# 5. Исключаем входящие VPN-порты роутера (Reality, XHTTP)
$IPT -A "$CHAIN" -p tcp -m multiport --dports 34442,34443,34444 -j RETURN

# 6. Прозрачное перенаправление целевых пулов обхода в прокси (O(1) через ipset)
# Meta / Instagram (все 34 суперсети AS32934)
$IPT -A "$CHAIN" -p tcp -m multiport --dports 80,443 -m set --match-set META_NETS dst -j REDIRECT --to-ports "$PROXY_PORT"

# Нейросети (ChatGPT, OpenAI, Gemini, Claude)
$IPT -A "$CHAIN" -p tcp -m multiport --dports 80,443 -m set --match-set AI_NETS dst -j REDIRECT --to-ports "$PROXY_PORT"

# Дополнительные сервисные адреса (Open-Meteo погода для thermo_logger, Osvault OTA)
$IPT -A "$CHAIN" -p tcp -d 157.90.83.168 -j REDIRECT --to-ports "$PROXY_PORT"
$IPT -A "$CHAIN" -p tcp -d 104.21.3.241 -j REDIRECT --to-ports "$PROXY_PORT"
$IPT -A "$CHAIN" -p tcp -d 172.67.131.89 -j REDIRECT --to-ports "$PROXY_PORT"
$IPT -A "$CHAIN" -p tcp -d 188.114.96.0/20 -j REDIRECT --to-ports "$PROXY_PORT"

# 7. Встраивание цепочки в PREROUTING и OUTPUT
$IPT -D PREROUTING -p tcp -j "$CHAIN" 2>/dev/null
$IPT -I PREROUTING 1 -p tcp -j "$CHAIN"

$IPT -D OUTPUT -p tcp -j "$CHAIN" 2>/dev/null
$IPT -I OUTPUT 1 -p tcp -j "$CHAIN"
