import socket
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Let's use dnspython or standard socket to parse
import struct

def query_dns(server, qname):
    # build DNS query
    ID = 0xAAAA
    flags = 0x0100 # RD
    qdcount = 1
    header = struct.pack('!HHHHHH', ID, flags, qdcount, 0, 0, 0)
    qbody = b''
    for part in qname.split('.'):
        qbody += bytes([len(part)]) + part.encode('ascii')
    qbody += b'\x00\x00\x01\x00\x01' # Type A, Class IN
    
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(3)
    s.sendto(header + qbody, (server, 53))
    data, _ = s.recvfrom(1024)
    
    # parse answers
    # header is 12 bytes
    ancount = struct.unpack('!H', data[6:8])[0]
    print(f"Server {server} -> Answer count: {ancount}")
    # skip question
    idx = 12 + len(qbody)
    for _ in range(ancount):
        # name pointer or label
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
            ip = socket.inet_ntoa(rdata)
            print(f"  A Record: {ip}")
        elif rtype == 5:
            print(f"  CNAME Record (len {rdlength})")

query_dns('5.175.161.3', 'chatgpt.com')
query_dns('5.175.161.3', 'openai.com')
query_dns('5.175.161.3', 'ya.ru')
