import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r'E:\Projects\Router_api\app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'port' in l.lower() and ('open' in l.lower() or 'href' in l.lower() or 'url' in l.lower() or 'btn' in l.lower()):
        print(f"{i+1}: {l.strip()}")
