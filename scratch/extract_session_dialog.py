import sys
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r'E:\Projects\Router_api\ses_e7de4ad6effdc1tpqZ6K3gVufy.json', 'r', encoding='utf-8', errors='replace') as f:
    data = json.load(f)

messages = data.get('messages', [])

print(f"Total messages in session: {len(messages)}\n")

for i, m in enumerate(messages):
    m_type = m.get('type')
    if m_type == 'user':
        print(f"\n================ USER MESSAGE #{i} ================")
        print(m.get('text', ''))
    elif m_type == 'assistant':
        # Check if this assistant message has text content (final response or significant text)
        content = m.get('content', [])
        texts = []
        for c in content:
            if isinstance(c, dict) and c.get('type') == 'text':
                texts.append(c.get('text', ''))
        full_text = "\n".join(texts).strip()
        if full_text and (len(full_text) > 300 or 'рекомендац' in full_text.lower() or 'p0' in full_text.lower()):
            print(f"\n--- ASSISTANT MESSAGE #{i} (len {len(full_text)}) ---")
            print(full_text[:500] + ("\n... [truncated] ..." if len(full_text) > 500 else ""))
