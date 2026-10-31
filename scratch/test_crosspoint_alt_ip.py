import sys
import socket
import ssl
import time

sys.stdout.reconfigure(encoding='utf-8')

# Test Cloudflare alternate Anycast IPs
alt_ips = [
    "104.21.5.197",
    "172.67.182.203",
    "104.26.12.148",
    "172.67.74.152",
    "162.159.153.4"
]

print("=== Тестирование доступности порта 443 на других Cloudflare IP с этого ПК ===")

for ip in alt_ips:
    t0 = time.time()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.5)
        s.connect((ip, 443))
        dt = (time.time() - t0) * 1000
        print(f"Подключение к {ip}:443 успешно за {dt:.1f} мс!")
        
        # Test TLS SNI crosspointreader.com
        ctx = ssl.create_default_context()
        ts = ctx.wrap_socket(s, server_hostname="crosspointreader.com")
        print(f"  TLS Handshake успешен с {ip} для crosspointreader.com!")
        
        # Send HTTP GET
        req = b"GET / HTTP/1.1\r\nHost: crosspointreader.com\r\nUser-Agent: Mozilla/5.0\r\nAccept: */*\r\nConnection: close\r\n\r\n"
        ts.sendall(req)
        resp = ts.recv(1024)
        print(f"  HTTP Ответ:\n{resp.decode('utf-8', errors='replace')[:200]}")
        ts.close()
        break
    except Exception as e:
        dt = (time.time() - t0) * 1000
        print(f"IP {ip} не ответил ({dt:.1f} мс): {e}")

