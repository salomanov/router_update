import sys
import socket
import struct

sys.stdout.reconfigure(encoding='utf-8')

servers = {
    "eu.geohide.ru (5.175.161.3)": "5.175.161.3",
    "xbox-dns.ru (157.22.178.170)": "157.22.178.170",
    "dns.dns-ai.ru (176.12.72.184)": "176.12.72.184",
    "Cloudflare (1.1.1.1)": "1.1.1.1",
    "Local Router (192.168.1.1)": "192.168.1.1"
}

def query_dns(name, server, qname):
    ID = 0xBEEF
    flags = 0x0100
    header = struct.pack('!HHHHHH', ID, flags, 1, 0, 0, 0)
    qbody = b''
    for part in qname.split('.'):
        qbody += bytes([len(part)]) + part.encode('ascii')
    qbody += b'\x00\x00\x01\x00\x01'
    
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(2.5)
    try:
        s.sendto(header + qbody, (server, 53))
        data, _ = s.recvfrom(1024)
        ancount = struct.unpack('!H', data[6:8])[0]
        idx = 12 + len(qbody)
        ips = []
        for _ in range(ancount):
            if data[idx] >= 192:
                idx += 2
            else:
                while data[idx] != 0:
                    idx += data[idx] + 1
                idx += 1
            rtype, rclass, ttl, rdlength = struct.unpack('!HHIH', data[idx:idx+10])
            idx += 10
            rdata = data[idx:idx+rdlength]
            idx += rdlength
            if rtype == 1 and rdlength == 4:
                ips.append(socket.inet_ntoa(rdata))
        print(f"{name:30} -> {ips}")
    except Exception as e:
        print(f"{name:30} -> Error: {e}")

for name, srv in servers.items():
    query_dns(name, srv, "crosspointreader.com")
