#!/bin/sh
[ "$type" = "ip6tables" ] && exit 0
[ "$table" != "filter" ] && exit 0

# Reject QUIC (UDP 443) globally for all network clients to force browsers and apps
# to use TCP 443 with nfqws2 Anti-DPI bypass. Prevents audio and video stuttering on YouTube.
iptables -C FORWARD -p udp --dport 443 -j REJECT --reject-with icmp-port-unreachable 2>/dev/null || iptables -I FORWARD -p udp --dport 443 -j REJECT --reject-with icmp-port-unreachable
