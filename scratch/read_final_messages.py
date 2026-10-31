import sys
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r'E:\Projects\Router_api\ses_e7de4ad6effdc1tpqZ6K3gVufy.json', 'r', encoding='utf-8', errors='replace') as f:
    data = json.load(f)

messages = data.get('messages', [])

for i in range(405, len(messages)):
    m = messages[i]
    m_type = m.get('type')
    print(f"\nMessage {i} (type: {m_type}):")
    content = m.get('content', [])
    if isinstance(content, list):
        for c in content:
            if isinstance(c, dict) and c.get('type') == 'text':
                print(c.get('text', ''))
    elif 'text' in m:
        print(m['text'])
