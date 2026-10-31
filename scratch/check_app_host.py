import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r'E:\Projects\Router_api\app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(565, 590):
    if i < len(lines):
        print(f"{i+1}: {lines[i].rstrip()}")
