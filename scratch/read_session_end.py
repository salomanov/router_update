import sys
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r'E:\Projects\Router_api\ses_e7de4ad6effdc1tpqZ6K3gVufy.json', 'r', encoding='utf-8', errors='replace') as f:
    data = json.load(f)

messages = data.get('messages', [])

for i in range(338, len(messages)):
    m = messages[i]
    m_type = m.get('type')
    if m_type == 'user':
        print(f"\n================ USER MESSAGE #{i} ================")
        print(m.get('text', ''))
    elif m_type == 'assistant':
        content = m.get('content', [])
        texts = []
        for c in content:
            if isinstance(c, dict) and c.get('type') == 'text':
                texts.append(c.get('text', ''))
        full_text = "\n".join(texts).strip()
        if full_text:
            print(f"\n--- ASSISTANT MESSAGE #{i} (len {len(full_text)}) ---")
            print(full_text[:1000] + ("\n... [truncated] ..." if len(full_text) > 1000 else ""))
