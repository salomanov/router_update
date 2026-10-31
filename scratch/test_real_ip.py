import sys
import socket
import ssl

sys.stdout.reconfigure(encoding='utf-8')

for ip in ['104.21.28.172', '172.67.146.236']:
    try:
        ctx = ssl.create_default_context()
        raw_s = socket.create_connection((ip, 443), timeout=5)
        s = ctx.wrap_socket(raw_s, server_hostname='crosspointreader.com')
        s.sendall(b"GET / HTTP/1.1\r\nHost: crosspointreader.com\r\nUser-Agent: Mozilla/5.0\r\nConnection: close\r\n\r\n")
        data = s.recv(4096)
        print(f"Response from real IP {ip}:")
        print(data.decode('utf-8', errors='replace')[:250])
        s.close()
    except Exception as e:
        print(f"Error for {ip}: {e}")
