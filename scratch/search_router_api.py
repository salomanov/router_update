import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r'E:\Projects\Router_api\router_api.py', 'r', encoding='utf-8') as f:
    code = f.read()

for i, line in enumerate(code.splitlines()):
    if 'update' in line.lower() or 'upgrade' in line.lower() or 'install' in line.lower():
        print(f"{i+1}: {line}")
