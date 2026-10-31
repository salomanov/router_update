import sys
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r'E:\Projects\Router_api\ses_e7de4ad6effdc1tpqZ6K3gVufy.json', 'r', encoding='utf-8', errors='replace') as f:
    data = json.load(f)

messages = data.get('messages', [])
for i in range(min(5, len(messages))):
    print(f"\n--- Message {i} keys: {list(messages[i].keys())} ---")
    for k, v in messages[i].items():
        if isinstance(v, (str, int, float, bool)):
            print(f"  {k}: {v}")
        elif isinstance(v, dict):
            print(f"  {k} (dict keys): {list(v.keys())}")
        elif isinstance(v, list):
            print(f"  {k} (list len): {len(v)}")
