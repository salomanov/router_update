import sys
import socket
import struct

sys.stdout.reconfigure(encoding='utf-8')

def query_dns(server, qname):
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
        print(f"DNS {server} -> {ips}")
    except Exception as e:
        print(f"DNS {server} -> Error: {e}")

query_dns("1.1.1.1", "crosspointreader.com")
query_dns("8.8.8.8", "crosspointreader.com")
query_dns("77.88.8.8", "crosspointreader.com")
query_dns("192.168.1.1", "crosspointreader.com")
