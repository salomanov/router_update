import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r'E:\Projects\Router_api\app.js', 'r', encoding='utf-8') as f:
    code = f.read()

for i, line in enumerate(code.splitlines()):
    if 'grouter' in line.lower() and ('updat' in line.lower() or 'install' in line.lower() or 'curl' in line.lower()):
        print(f"{i+1}: {line}")
