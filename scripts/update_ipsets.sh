#!/bin/sh
# RouterKit Universal Core: Atomic IPSET updater
# Guarantees zero session drops via kernel-level ipset swap
# Reference: Router_Workspace/etalon/ipsets/update_ipsets.sh
export LC_ALL=C
export LANG=C
PATH="/opt/sbin:/opt/bin:/opt/usr/bin:/usr/sbin:/usr/bin:/sbin:/bin"

LOCKFILE="/tmp/update_ipsets.lock"
if ! mkdir "$LOCKFILE" 2>/dev/null; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Another update process is running. Exiting."
    exit 0
fi
trap 'rm -rf "$LOCKFILE"' EXIT

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting atomic ipset update..."

# ==========================================
# 1. AI_NETS (ChatGPT, OpenAI, Gemini, Claude)
# ==========================================
AI_DOMAINS="chatgpt.com ab.chatgpt.com ws.chatgpt.com auth.openai.com auth0.openai.com openai.com api.openai.com oaistatic.com cdn.oaistatic.com oaiusercontent.com files.oaiusercontent.com gemini.google.com aistudio.google.com alkalimakersuite-pa.clients6.google.com generativelanguage.googleapis.com claude.ai anthropic.com"

ipset create AI_NETS hash:ip -exist
ipset create AI_NETS_TMP hash:ip -exist
ipset flush AI_NETS_TMP

# Known static upstream SNI proxy
ipset add AI_NETS_TMP 31.58.216.201 -exist 2>/dev/null

for d in $AI_DOMAINS; do
    ips=$(nslookup "$d" 127.0.0.1 2>/dev/null | awk '/^Address [0-9]+:/{print $3}' | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$')
    for ip in $ips; do
        case "$ip" in
            127.*|10.*|192.168.*|172.1[6-9].*|172.2[0-9].*|172.3[0-1].*|0.*)
                continue
                ;;
        esac
        ipset add AI_NETS_TMP "$ip" -exist 2>/dev/null
    done
done

TMP_COUNT=$(ipset list AI_NETS_TMP | grep -E '^[0-9]+\.' | wc -l)
if [ "$TMP_COUNT" -gt 0 ]; then
    ipset swap AI_NETS AI_NETS_TMP
    ipset destroy AI_NETS_TMP 2>/dev/null
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [OK] AI_NETS swapped atomically. Active IPs: $TMP_COUNT"
else
    ipset destroy AI_NETS_TMP 2>/dev/null
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARN] AI_NETS_TMP empty. Keeping existing set."
fi

# ==========================================
# 2. META_NETS (All 34 Meta AS32934 supernets)
# ==========================================
ipset create META_NETS hash:net -exist
ipset create META_NETS_TMP hash:net -exist
ipset flush META_NETS_TMP

META_SUPERNETS="
31.13.24.0/21
31.13.64.0/18
45.64.40.0/22
57.141.0.0/24
57.141.2.0/23
57.141.4.0/23
57.141.6.0/24
57.141.8.0/24
57.141.10.0/24
57.141.12.0/23
57.141.14.0/24
57.141.16.0/22
57.141.20.0/24
57.141.22.0/24
57.141.24.0/24
57.144.0.0/14
66.220.144.0/20
69.63.176.0/20
69.171.224.0/19
74.119.76.0/22
102.132.96.0/20
103.4.96.0/22
129.134.0.0/17
157.240.0.0/17
157.240.192.0/18
163.70.128.0/17
163.77.132.0/23
163.77.136.0/23
163.77.160.0/20
173.252.64.0/18
179.60.192.0/22
185.60.216.0/22
185.89.216.0/22
204.15.20.0/22
"

META_COUNT=0
for net in $META_SUPERNETS; do
    ipset add META_NETS_TMP "$net" -exist 2>/dev/null
    META_COUNT=$((META_COUNT + 1))
done

if [ "$META_COUNT" -ge 30 ]; then
    ipset swap META_NETS META_NETS_TMP
    ipset destroy META_NETS_TMP 2>/dev/null
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [OK] META_NETS swapped atomically. Active supernets: $META_COUNT"
else
    ipset destroy META_NETS_TMP 2>/dev/null
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARN] META_NETS_TMP incomplete. Keeping existing set."
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] IPSET atomic update finished successfully."
