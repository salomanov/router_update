import socket
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("Resolved IP on Windows right now:", socket.gethostbyname_ex('crosspointreader.com'))
