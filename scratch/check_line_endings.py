import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r'E:\Projects\Router_api\install.sh', 'rb') as f:
    raw = f.read()

# Check line endings
print("CRLF count:", raw.count(b'\r\n'))
print("LF count:", raw.count(b'\n'))
