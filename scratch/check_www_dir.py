import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r'E:\Projects\Router_api\router_api.py', 'r', encoding='utf-8') as f:
    text = f.read()

for i, l in enumerate(text.splitlines()):
    if 'index.html' in l or 'www' in l.lower() or 'static' in l.lower() or 'share' in l.lower():
        print(f"{i+1}: {l}")
