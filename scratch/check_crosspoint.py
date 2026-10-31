import sys
import socket
import ssl
import time
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding='utf-8')

TARGET_HOST = "crosspointreader.com"
TARGET_URL = "https://crosspointreader.com/"

print(f"=== Проверка доступности: {TARGET_URL} на этом ПК ===")

# 1. DNS Resolution
print("\n--- 1. Резолвинг DNS ---")
try:
    host_info = socket.gethostbyname_ex(TARGET_HOST)
    print(f"Имя: {host_info[0]}")
    print(f"Псевдонимы: {host_info[1]}")
    print(f"IP-адреса: {host_info[2]}")
    target_ips = host_info[2]
except Exception as e:
    print(f"Ошибка DNS-резолвинга: {e}")
    target_ips = []

# 2. TCP Port 443 Connect
print("\n--- 2. Проверка TCP-соединения (порт 443) ---")
connected_ip = None
for ip in target_ips:
    t0 = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect((ip, 443))
        dt = (time.time() - t0) * 1000
        print(f"Подключение к {ip}:443 успешно за {dt:.1f} мс")
        connected_ip = ip
        sock.close()
        break
    except Exception as e:
        dt = (time.time() - t0) * 1000
        print(f"Не удалось подключиться к {ip}:443 за {dt:.1f} мс: {e}")

# 3. TLS Handshake
print("\n--- 3. Проверка TLS 1.3 / 1.2 Handshake ---")
if connected_ip:
    t0 = time.time()
    try:
        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_sock.settimeout(6.0)
        raw_sock.connect((connected_ip, 443))
        ctx = ssl.create_default_context()
        tls_sock = ctx.wrap_socket(raw_sock, server_hostname=TARGET_HOST)
        dt = (time.time() - t0) * 1000
        print(f"TLS Handshake успешен за {dt:.1f} мс!")
        print(f"Версия TLS: {tls_sock.version()}")
        print(f"Шифр: {tls_sock.cipher()}")
        cert = tls_sock.getpeercert()
        print(f"Сертификат выдан для: {cert.get('subject')}")
        tls_sock.close()
    except Exception as e:
        dt = (time.time() - t0) * 1000
        print(f"Ошибка TLS Handshake ({dt:.1f} мс): {e}")

# 4. HTTP / HTTPS Request
print("\n--- 4. HTTP/HTTPS GET запрос ---")
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
}

req = urllib.request.Request(TARGET_URL, headers=headers)
t0 = time.time()
try:
    with urllib.request.urlopen(req, timeout=10.0) as resp:
        dt = (time.time() - t0) * 1000
        status_code = resp.status
        reason = resp.reason
        content_type = resp.headers.get("Content-Type", "")
        content_length = resp.headers.get("Content-Length", "unknown")
        server = resp.headers.get("Server", "unknown")
        final_url = resp.geturl()
        body = resp.read()
        print(f"HTTP Статус: {status_code} {reason}")
        print(f"Время ответа: {dt:.1f} мс")
        print(f"Итоговый URL: {final_url}")
        print(f"Server: {server}")
        print(f"Content-Type: {content_type}")
        print(f"Размер ответа: {len(body)} байт")
        print("\nПервые 300 символов ответа:")
        try:
            print(body[:300].decode('utf-8', errors='replace'))
        except Exception:
            print(body[:300])
except urllib.error.HTTPError as e:
    dt = (time.time() - t0) * 1000
    print(f"HTTP Ошибка {e.code} {e.reason} ({dt:.1f} мс)")
    print(f"Заголовки: {e.headers}")
    err_body = e.read()
    print(f"Тело ошибки: {err_body[:300].decode('utf-8', errors='replace')}")
except Exception as e:
    dt = (time.time() - t0) * 1000
    print(f"Сбой запроса ({dt:.1f} мс): {e}")

print("\n=== Проверка завершена ===")
