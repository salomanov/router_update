import socket
import sys

sys.stdout.reconfigure(encoding='utf-8')

host = "eu.geohide.ru"
try:
    ips = socket.gethostbyname_ex(host)
    print(f"Host: {host}")
    print(f"IPs: {ips}")
except Exception as e:
    print(f"Error resolving {host}: {e}")
