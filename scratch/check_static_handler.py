import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r'E:\Projects\Router_api\router_api.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(725, min(len(lines), 755)):
    print(f"{i+1}: {lines[i].rstrip()}")
