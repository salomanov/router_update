import sys
import socket

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ip = "178.140.8.56"
port = 34222

print(f"Connecting to {ip}:{port}...")
s = socket.socket()
s.settimeout(5)
try:
    s.connect((ip, port))
    banner = s.recv(1024)
    print(f"Connected! Received banner: {banner}")
except Exception as e:
    print(f"Failed to connect: {e}")
finally:
    s.close()
