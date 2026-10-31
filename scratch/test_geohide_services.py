import socket
import ssl
import sys
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')

# Check DNS over UDP 53
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(2)
# DNS query for chatgpt.com
# Transaction ID: 0x1234, Flags: 0x0100 (standard query), Questions: 1, Answer RRs: 0, Authority RRs: 0, Additional RRs: 0
query = b'\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x07chatgpt\x03com\x00\x00\x01\x00\x01'

target_ip = '5.175.161.3'
print(f"Testing DNS UDP 53 on {target_ip}...")
try:
    s.sendto(query, (target_ip, 53))
    data, addr = s.recvfrom(512)
    print(f"Received {len(data)} bytes via UDP 53!")
except Exception as e:
    print(f"UDP 53 failed: {e}")

# Check DoT (port 853)
print(f"\nTesting DoT 853 on eu.geohide.ru...")
try:
    sock = socket.create_connection(('eu.geohide.ru', 853), timeout=3)
    ctx = ssl.create_default_context()
    ssock = ctx.wrap_socket(sock, server_hostname='eu.geohide.ru')
    print("DoT 853 connection successful!")
    ssock.close()
except Exception as e:
    print(f"DoT 853 failed: {e}")

# Check DoH (port 443)
print(f"\nTesting DoH on https://eu.geohide.ru/dns-query ...")
try:
    req = urllib.request.Request("https://eu.geohide.ru/dns-query?name=chatgpt.com", headers={"Accept": "application/dns-json", "User-Agent": "curl/8.0"})
    with urllib.request.urlopen(req, timeout=3) as resp:
        print("DoH Status:", resp.status)
        print("DoH Body:", resp.read().decode('utf-8', errors='replace')[:200])
except Exception as e:
    print(f"DoH query failed: {e}")
