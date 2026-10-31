import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r'E:\Projects\Router_api\app.js', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.splitlines()
for i, line in enumerate(lines):
    if ':90' in line or 'nfqws' in line.lower() or 'lighttpd' in line.lower():
        print(f"app.js:{i+1}: {line}")
