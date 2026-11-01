#!/bin/sh
# L2TP VPN Optimization & Fix for YouTube / Streaming

# 1. Clamp TCP MSS to 1360 for L2TP (MTU 1400 - 40 header = 1360) to prevent packet drops on video streams
iptables -t mangle -C FORWARD -i l2tp+ -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1360 2>/dev/null || iptables -t mangle -I FORWARD -i l2tp+ -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1360
iptables -t mangle -C FORWARD -o l2tp+ -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1360 2>/dev/null || iptables -t mangle -I FORWARD -o l2tp+ -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1360

# 2. Reject QUIC (UDP 443) from L2TP clients so browsers immediately fallback to TCP with Anti-DPI desync
iptables -C FORWARD -i l2tp+ -p udp --dport 443 -j REJECT --reject-with icmp-port-unreachable 2>/dev/null || iptables -I FORWARD -i l2tp+ -p udp --dport 443 -j REJECT --reject-with icmp-port-unreachable

# 3. Reject IPv6 forwarding on L2TP to eliminate Happy Eyeballs / IPv6 timeouts
ip6tables -C FORWARD -i l2tp+ -j REJECT --reject-with icmp6-port-unreachable 2>/dev/null || ip6tables -I FORWARD -i l2tp+ -j REJECT --reject-with icmp6-port-unreachable
ip6tables -C FORWARD -o l2tp+ -j REJECT --reject-with icmp6-port-unreachable 2>/dev/null || ip6tables -I FORWARD -o l2tp+ -j REJECT --reject-with icmp6-port-unreachable

# 4. Redirect plain DNS to router's resolver
iptables -t nat -C PREROUTING -i l2tp+ -p udp --dport 53 -j REDIRECT --to-ports 53 2>/dev/null || iptables -t nat -I PREROUTING -i l2tp+ -p udp --dport 53 -j REDIRECT --to-ports 53
iptables -t nat -C PREROUTING -i l2tp+ -p tcp --dport 53 -j REDIRECT --to-ports 53 2>/dev/null || iptables -t nat -I PREROUTING -i l2tp+ -p tcp --dport 53 -j REDIRECT --to-ports 53
