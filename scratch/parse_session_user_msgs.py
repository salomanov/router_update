import sys
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r'E:\Projects\Router_api\ses_e7de4ad6effdc1tpqZ6K3gVufy.json', 'r', encoding='utf-8', errors='replace') as f:
    data = json.load(f)

messages = data.get('messages', [])

# Find user messages
user_msgs = []
for i, m in enumerate(messages):
    role = m.get('role') or m.get('author') or (m.get('sender', {}).get('type'))
    # check if user
    text = ""
    if 'content' in m:
        c = m['content']
        if isinstance(c, str):
            text = c
        elif isinstance(c, list):
            for part in c:
                if isinstance(part, dict) and 'text' in part:
                    text += part['text'] + "\n"
    elif 'text' in m:
        text = m['text']
        
    if m.get('role') == 'user' or (isinstance(role, str) and 'user' in role.lower()):
        user_msgs.append((i, text[:300]))

print(f"Total messages: {len(messages)}, User messages count: {len(user_msgs)}")
for idx, txt in user_msgs[:15]:
    print(f"[{idx}]: {txt.strip()}\n")
