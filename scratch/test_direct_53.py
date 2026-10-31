import sys
import socket
import struct

sys.stdout.reconfigure(encoding='utf-8')

ID = 0xBEEF
flags = 0x0100
header = struct.pack('!HHHHHH', ID, flags, 1, 0, 0, 0)
qbody = b''
for part in 'crosspointreader.com'.split('.'):
    qbody += bytes([len(part)]) + part.encode('ascii')
qbody += b'\x00\x00\x01\x00\x01'

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(2.5)
s.sendto(header + qbody, ('192.168.1.1', 53))
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
print("192.168.1.1 returned:", ips)
