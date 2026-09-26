#!/bin/sh
iptables -C INPUT -i tailscale0 -j ACCEPT 2>/dev/null || iptables -I INPUT -i tailscale0 -j ACCEPT
iptables -C FORWARD -i tailscale0 -j ACCEPT 2>/dev/null || iptables -I FORWARD -i tailscale0 -j ACCEPT
iptables -C FORWARD -o tailscale0 -j ACCEPT 2>/dev/null || iptables -I FORWARD -o tailscale0 -j ACCEPT

# 1. Reject QUIC (UDP 443) from tailscale0 to force apps to fallback to TCP with DPI bypass instantly
iptables -C FORWARD -i tailscale0 -p udp --dport 443 -j REJECT --reject-with icmp-port-unreachable 2>/dev/null || iptables -I FORWARD -i tailscale0 -p udp --dport 443 -j REJECT --reject-with icmp-port-unreachable

# 2. Reject dead ISP block stubs (e.g. ER-Telecom / Dom.ru spoofing IP) immediately with RST
iptables -C FORWARD -d 188.186.146.207 -p tcp -j REJECT --reject-with tcp-reset 2>/dev/null || iptables -I FORWARD -d 188.186.146.207 -p tcp -j REJECT --reject-with tcp-reset

# 3. Intercept all plain DNS from Tailscale and redirect to router's secure DoH resolver
iptables -t nat -C PREROUTING -i tailscale0 -p udp --dport 53 -j REDIRECT --to-ports 53 2>/dev/null || iptables -t nat -I PREROUTING -i tailscale0 -p udp --dport 53 -j REDIRECT --to-ports 53
iptables -t nat -C PREROUTING -i tailscale0 -p tcp --dport 53 -j REDIRECT --to-ports 53 2>/dev/null || iptables -t nat -I PREROUTING -i tailscale0 -p tcp --dport 53 -j REDIRECT --to-ports 53

# 4. Clamp TCP MSS for Tailscale (MTU 1280) to 1240 to prevent packet drops and fragmentation
iptables -t mangle -C FORWARD -o tailscale0 -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1240 2>/dev/null || iptables -t mangle -I FORWARD -o tailscale0 -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1240
iptables -t mangle -C FORWARD -i tailscale0 -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1240 2>/dev/null || iptables -t mangle -I FORWARD -i tailscale0 -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1240

# 5. Reject IPv6 forwarding from tailscale0 immediately to eliminate Happy Eyeballs timeouts
ip6tables -C FORWARD -i tailscale0 -j REJECT --reject-with icmp6-port-unreachable 2>/dev/null || ip6tables -I FORWARD -i tailscale0 -j REJECT --reject-with icmp6-port-unreachable

# 6. NAT masquerade for Exit Node
iptables -t nat -C POSTROUTING -s 100.64.0.0/10 -j MASQUERADE 2>/dev/null || iptables -t nat -I POSTROUTING -s 100.64.0.0/10 -j MASQUERADE
iptables -t nat -C POSTROUTING -o ppp0 -j MASQUERADE 2>/dev/null || iptables -t nat -I POSTROUTING -o ppp0 -j MASQUERADE