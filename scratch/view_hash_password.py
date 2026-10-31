import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r'E:\Projects\Router_api\router_api.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('def hash_password')
print(text[idx:idx+800])
