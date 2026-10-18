#!/bin/sh
[ "$table" != "filter" ] && exit 0

# Reject QUIC (UDP 443) globally for all IPv4 and IPv6 network clients to force browsers and apps
# to use TCP 443 with nfqws2 Anti-DPI bypass. Prevents audio and video stuttering on YouTube.
if [ "$type" = "ip6tables" ]; then
    ip6tables -C FORWARD -p udp --dport 443 -j REJECT --reject-with icmp6-port-unreachable 2>/dev/null || ip6tables -I FORWARD -p udp --dport 443 -j REJECT --reject-with icmp6-port-unreachable
else
    iptables -C FORWARD -p udp --dport 443 -j REJECT --reject-with icmp-port-unreachable 2>/dev/null || iptables -I FORWARD -p udp --dport 443 -j REJECT --reject-with icmp-port-unreachable
fi
