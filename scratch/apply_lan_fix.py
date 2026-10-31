import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')

HOST = "178.140.8.56"
PORT = 34222
USER = "root"
PASS = "keenetic"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=12)

# 1. Update exclude.list: fix setka.news and add kaspersky
update_exclude_cmd = """
sed -i 's/setka\\.newsamazonaws\\.com/setka.news\\namazonaws.com/' /opt/etc/nfqws2/lists/exclude.list
grep -q '^kaspersky\\.com' /opt/etc/nfqws2/lists/exclude.list || echo 'kaspersky.com' >> /opt/etc/nfqws2/lists/exclude.list
grep -q '^kaspersky-labs\\.com' /opt/etc/nfqws2/lists/exclude.list || echo 'kaspersky-labs.com' >> /opt/etc/nfqws2/lists/exclude.list
tail -n 10 /opt/etc/nfqws2/lists/exclude.list
"""

# 2. Create /opt/etc/ndm/netfilter.d/005-lan-fix.sh
lan_script = """#!/bin/sh
# LAN & Wi-Fi (br0) Optimization: DNS redirection, IPv6 instant reject, QUIC block, TCP MSS clamping

# 1. DNS REDIRECTION:
# Intercept all plain DNS queries (UDP and TCP 53) from LAN (br0) and redirect to router's ndnproxy (port 53).
# Guarantees that all LAN devices use GeoHide SmartDNS for ChatGPT/Gemini and avoid ISP DNS filtering.
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
"""

full_cmd = f"""
echo "=== 1. Updating exclude.list ==="
{update_exclude_cmd}

echo "=== 2. Writing /opt/etc/ndm/netfilter.d/005-lan-fix.sh ==="
cat << 'EOF' > /opt/etc/ndm/netfilter.d/005-lan-fix.sh
{lan_script}
EOF
chmod +x /opt/etc/ndm/netfilter.d/005-lan-fix.sh

echo "=== 3. Executing /opt/etc/ndm/netfilter.d/005-lan-fix.sh ==="
/opt/etc/ndm/netfilter.d/005-lan-fix.sh

echo "=== 4. Restarting nfqws2 ==="
/opt/etc/init.d/S51nfqws2 restart

echo "=== 5. Checking active rules ==="
echo "--- NAT PREROUTING ---"
iptables -t nat -L PREROUTING -n -v --line-numbers | head -n 12
echo "--- FORWARD (IPv4) ---"
iptables -L FORWARD -n -v --line-numbers | head -n 12
echo "--- FORWARD (IPv6) ---"
ip6tables -L FORWARD -n -v --line-numbers | head -n 12
echo "--- MANGLE FORWARD ---"
iptables -t mangle -L FORWARD -n -v --line-numbers | head -n 10
"""

stdin, stdout, stderr = client.exec_command(full_cmd)
print(stdout.read().decode('utf-8', errors='replace'))
client.close()
