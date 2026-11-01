#!/bin/sh
# LAN & Wi-Fi (br0) Optimization: DNS redirection, IPv6 instant reject, QUIC block, TCP MSS clamping

# 1. DNS REDIRECTION:
# Intercept all plain DNS queries (UDP and TCP 53) from LAN (br0) and redirect to router's ndnproxy (port 53).
# Guarantees that all LAN devices use Keenetic's DoH/DoT SmartDNS and avoid ISP DNS filtering.
iptables -t nat -C PREROUTING -i br0 -p udp --dport 53 -j REDIRECT --to-ports 53 2>/dev/null || iptables -t nat -I PREROUTING -i br0 -p udp --dport 53 -j REDIRECT --to-ports 53
iptables -t nat -C PREROUTING -i br0 -p tcp --dport 53 -j REDIRECT --to-ports 53 2>/dev/null || iptables -t nat -I PREROUTING -i br0 -p tcp --dport 53 -j REDIRECT --to-ports 53

# 2. REJECT DoT (DNS over TLS, port 853) with TCP reset so clients immediately fallback to standard DNS:
iptables -C FORWARD -i br0 -p tcp --dport 853 -j REJECT --reject-with tcp-reset 2>/dev/null || iptables -I FORWARD -i br0 -p tcp --dport 853 -j REJECT --reject-with tcp-reset

# 3. REJECT QUIC (UDP 443) from br0 with icmp-port-unreachable so browsers instantly fallback to TCP HTTPS:
iptables -C FORWARD -i br0 -p udp --dport 443 -j REJECT --reject-with icmp-port-unreachable 2>/dev/null || iptables -I FORWARD -i br0 -p udp --dport 443 -j REJECT --reject-with icmp-port-unreachable

# 4. REJECT IPv6 FORWARDING from br0 immediately:
# Eliminates Happy Eyeballs / IPv6 timeouts on dual-stack hosts since WAN has no IPv6 route.
ip6tables -C FORWARD -i br0 -j REJECT --reject-with icmp6-port-unreachable 2>/dev/null || ip6tables -I FORWARD -i br0 -j REJECT --reject-with icmp6-port-unreachable

# 5. TCP MSS CLAMPING to PMTU:
# Clamps MSS to prevent packet drops and fragmentation on large TLS certificates (Instagram, ChatGPT, YouTube).
iptables -t mangle -C FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu 2>/dev/null || iptables -t mangle -I FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu
