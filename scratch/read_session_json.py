import sys
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r'E:\Projects\Router_api\ses_e7de4ad6effdc1tpqZ6K3gVufy.json', 'r', encoding='utf-8', errors='replace') as f:
    data = json.load(f)

print("Type of data:", type(data))
if isinstance(data, dict):
    print("Keys:", list(data.keys()))
    # If it has messages or steps
    for k in ['messages', 'steps', 'history', 'turns', 'chat']:
        if k in data:
            print(f"Key {k} has len: {len(data[k])}")
elif isinstance(data, list):
    print("List len:", len(data))
    if len(data) > 0 and isinstance(data[0], dict):
        print("First item keys:", list(data[0].keys()))
