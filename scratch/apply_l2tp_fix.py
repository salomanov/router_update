import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')

HOST = "178.140.8.56"
PORT = 34222
USER = "root"
PASS = "keenetic"

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
    
    # Create persistent hook in /opt/etc/ndm/netfilter.d/015-l2tp.sh
    script_content = """#!/bin/sh
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
"""

    stdin, stdout, stderr = client.exec_command("cat > /opt/etc/ndm/netfilter.d/015-l2tp.sh && chmod +x /opt/etc/ndm/netfilter.d/015-l2tp.sh")
    stdin.write(script_content)
    stdin.channel.shutdown_write()
    stdout.read()

    # Execute it now
    stdin, stdout, stderr = client.exec_command("/opt/etc/ndm/netfilter.d/015-l2tp.sh")
    print(stdout.read().decode('utf-8', errors='replace'))
    err = stderr.read().decode('utf-8', errors='replace')
    if err:
        print("ERR:", err)

    # Verify rules are present
    cmd = """
    echo "=== Mangle TCPMSS ==="
    iptables -t mangle -L FORWARD -n -v | grep -i 'tcpmss\\|l2tp'
    echo "=== Filter FORWARD QUIC/L2TP ==="
    iptables -L FORWARD -n -v | grep -i 'l2tp'
    echo "=== ip6tables FORWARD L2TP ==="
    ip6tables -L FORWARD -n -v | grep -i 'l2tp'
    """
    stdin, stdout, stderr = client.exec_command(cmd)
    print(stdout.read().decode('utf-8', errors='replace'))

    client.close()

if __name__ == "__main__":
    run()
