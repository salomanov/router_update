import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

file_path = r"E:\Projects\Router_api\ChatExport_2026-10-31\result.json"

with open(file_path, "r", encoding="utf-8", errors="replace") as f:
    data = json.load(f)

messages = data.get("messages", [])

print("Searching messages mentioning 'google' from entire export...")

found = []
for msg in messages:
    date = msg.get("date", "")
    text = msg.get("text", "")
    if isinstance(text, list):
        text_str = ""
        for item in text:
            if isinstance(item, str):
                text_str += item
            elif isinstance(item, dict):
                text_str += item.get("text", "")
        text = text_str
    
    tl = text.lower()
    if ("гугл" in tl or "google" in tl) and any(w in tl for w in ["не работ", "лежит", "блокир", "отвал", "ошибк", "сломал"]):
        found.append((date, msg.get("from", "Anon"), text))

print(f"Found {len(found)} messages:")
for d, u, t in found[-15:]:
    print(f"[{d}] {u}:\n{t}\n" + "="*50)
