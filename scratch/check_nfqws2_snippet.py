import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r'E:\Projects\Router_api\install_nfqws2.sh', 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.splitlines()
for i in range(88, 116):
    print(f"{i+1}: {repr(lines[i])}")
