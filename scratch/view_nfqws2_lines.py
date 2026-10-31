import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r'E:\Projects\Router_api\install_nfqws2.sh', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(85, min(len(lines), 135)):
    print(f"{i+1}: {lines[i].rstrip()}")
