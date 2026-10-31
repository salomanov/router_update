import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r'E:\Projects\Router_api\install.sh', 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.splitlines()
for i, l in enumerate(lines):
    if '/opt/share/www' in l or '80-nfqws' in l or 'lighttpd' in l:
        print(f"install.sh:{i+1}: {l}")
