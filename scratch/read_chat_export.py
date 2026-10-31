import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

file_path = r"E:\Projects\Router_api\ChatExport_2026-10-31\result.json"

try:
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        data = json.load(f)

    chat_name = data.get("name", "Unknown")
    chat_type = data.get("type", "Unknown")
    messages = data.get("messages", [])
    print(f"Chat Name: {chat_name}")
    print(f"Chat Type: {chat_type}")
    print(f"Total messages: {len(messages)}")

    # Print the last 25 messages
    print("\n=== Last 25 messages ===")
    for msg in messages[-25:]:
        date = msg.get("date", "")
        from_user = msg.get("from", "Unknown")
        text = msg.get("text", "")
        if isinstance(text, list):
            # sometimes telegram texts are rich text elements
            text_str = ""
            for item in text:
                if isinstance(item, str):
                    text_str += item
                elif isinstance(item, dict):
                    text_str += item.get("text", "")
            text = text_str
        print(f"[{date}] {from_user}: {text}")
        if msg.get("photo"):
            print(f"  [Photo: {msg.get('photo')}]")

except Exception as e:
    print(f"Error reading {file_path}: {e}")
