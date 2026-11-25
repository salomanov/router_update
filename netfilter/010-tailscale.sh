#!/bin/sh
# Tailscale NAT, Firewall and Routing Integration for KeeneticOS
# Auto-applied on every netfilter/interface event

# Auto-detect WAN interface and LAN bridge/subnet
WAN_IF=$(route -n 2>/dev/null | awk '$1=="0.0.0.0"{print $8; exit}')
[ -z "$WAN_IF" ] && WAN_IF=$(ip route show default 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="dev") {print $(i+1); exit}}')
[ -z "$WAN_IF" ] && WAN_IF="ppp0"

LAN_IF="br0"
ip -4 addr show br0 >/dev/null 2>&1 || LAN_IF="br-lan"
LAN_IP=$(ip -4 addr show "$LAN_IF" 2>/dev/null | awk '/inet /{print $2}' | cut -d/ -f1 | head -n1)
[ -z "$LAN_IP" ] && LAN_IP="192.168.1.1"
LAN_SUBNET=$(echo "$LAN_IP" | awk -F. '{printf "%s.%s.%s.0/24", $1, $2, $3}')

# 1. Allow WireGuard UDP listening port from WAN and local tailscale0
iptables -C INPUT -p udp --dport 41641 -j ACCEPT 2>/dev/null || iptables -I INPUT 1 -p udp --dport 41641 -j ACCEPT
iptables -C INPUT -i tailscale0 -j ACCEPT 2>/dev/null || iptables -I INPUT 1 -i tailscale0 -j ACCEPT

# 2. Forwarding between tailscale0 and WAN / LAN
iptables -C FORWARD -i tailscale0 -j ACCEPT 2>/dev/null || iptables -I FORWARD 1 -i tailscale0 -j ACCEPT
iptables -C FORWARD -o tailscale0 -j ACCEPT 2>/dev/null || iptables -I FORWARD 2 -o tailscale0 -j ACCEPT

# 3. Keep YTGGC_RST and QUIC block ABOVE tailscale0 ACCEPT so Exit Node clients hit them too
if iptables -L YTGGC_RST >/dev/null 2>&1; then
    iptables -D FORWARD -j YTGGC_RST 2>/dev/null
    iptables -I FORWARD 1 -j YTGGC_RST
fi
iptables -D FORWARD -p udp --dport 443 -j REJECT --reject-with icmp-port-unreachable 2>/dev/null
iptables -I FORWARD 1 -p udp --dport 443 -j REJECT --reject-with icmp-port-unreachable

# 4. DNS: Allow Tailscale MagicDNS (100.100.100.100) first, then redirect remaining DNS to local router DNS
iptables -t nat -C PREROUTING -i tailscale0 -d 100.100.100.100 -p udp --dport 53 -j ACCEPT 2>/dev/null || iptables -t nat -I PREROUTING 1 -i tailscale0 -d 100.100.100.100 -p udp --dport 53 -j ACCEPT
iptables -t nat -C PREROUTING -i tailscale0 -d 100.100.100.100 -p tcp --dport 53 -j ACCEPT 2>/dev/null || iptables -t nat -I PREROUTING 2 -i tailscale0 -d 100.100.100.100 -p tcp --dport 53 -j ACCEPT
iptables -t nat -C PREROUTING -i tailscale0 -p udp --dport 53 -j REDIRECT --to-ports 53 2>/dev/null || iptables -t nat -A PREROUTING -i tailscale0 -p udp --dport 53 -j REDIRECT --to-ports 53
iptables -t nat -C PREROUTING -i tailscale0 -p tcp --dport 53 -j REDIRECT --to-ports 53 2>/dev/null || iptables -t nat -A PREROUTING -i tailscale0 -p tcp --dport 53 -j REDIRECT --to-ports 53

# 5. TCP MSS Clamping for WireGuard MTU 1280 over PPPoE/LTE (1200 in both directions avoids fragmentation)
iptables -t mangle -D FORWARD -i tailscale0 -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu 2>/dev/null
iptables -t mangle -D FORWARD -o tailscale0 -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1240 2>/dev/null
iptables -t mangle -D FORWARD -i tailscale0 -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1240 2>/dev/null
iptables -t mangle -C FORWARD -i tailscale0 -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1200 2>/dev/null || iptables -t mangle -I FORWARD 1 -i tailscale0 -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1200
iptables -t mangle -C FORWARD -o tailscale0 -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1200 2>/dev/null || iptables -t mangle -I FORWARD 2 -o tailscale0 -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1200

# 6. IPv6 Fast Fallback (Instant TCP RST so Android Happy Eyeballs switches to IPv4 without delay)
ip6tables -C FORWARD -i tailscale0 -p tcp -j REJECT --reject-with tcp-reset 2>/dev/null || ip6tables -I FORWARD 1 -i tailscale0 -p tcp -j REJECT --reject-with tcp-reset
ip6tables -C FORWARD -i tailscale0 -j REJECT --reject-with icmp6-port-unreachable 2>/dev/null || ip6tables -I FORWARD 2 -i tailscale0 -j REJECT --reject-with icmp6-port-unreachable

# 7. NAT Masquerade for Exit Node traffic routed to WAN
iptables -t nat -C POSTROUTING -s 100.64.0.0/10 -o "$WAN_IF" -j MASQUERADE 2>/dev/null || iptables -t nat -I POSTROUTING 1 -s 100.64.0.0/10 -o "$WAN_IF" -j MASQUERADE
iptables -t nat -C POSTROUTING -o "$WAN_IF" -j MASQUERADE 2>/dev/null || iptables -t nat -A POSTROUTING -o "$WAN_IF" -j MASQUERADE

# 8. NAT Masquerade for Tailscale Subnet Router traffic to LAN
# Ensures LAN hosts running local VPNs (e.g. AdGuard VPN) reply to router LAN IP
iptables -t nat -C POSTROUTING -s 100.64.0.0/10 -d "$LAN_SUBNET" -o "$LAN_IF" -j MASQUERADE 2>/dev/null || iptables -t nat -I POSTROUTING 1 -s 100.64.0.0/10 -d "$LAN_SUBNET" -o "$LAN_IF" -j MASQUERADE
