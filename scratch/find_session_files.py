import sys
import os
import glob

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def scan_dir(dir_path):
    print(f"\n=== Scanning {dir_path} ===")
    if not os.path.exists(dir_path):
        print("Directory does not exist")
        return
    for root, dirs, files in os.walk(dir_path):
        # Skip git and cache
        if '.git' in root or '__pycache__' in root or 'node_modules' in root:
            continue
        for f in files:
            full_path = os.path.join(root, f)
            try:
                mtime = os.path.getmtime(full_path)
                size = os.path.getsize(full_path)
                # Show files modified today or text/md/json/html/log files
                lower = f.lower()
                if any(lower.endswith(ext) for ext in ['.md', '.txt', '.json', '.html', '.log', '.doc', '.docx', '.session', '.chat']) or 'session' in lower or 'export' in lower or 'chat' in lower or 'отчет' in lower or 'проверк' in lower:
                    print(f"{full_path} (size: {size}, mtime: {mtime})")
            except Exception as e:
                pass

scan_dir(r"c:\Users\Salomanov\Desktop\Роутер")
scan_dir(r"E:\Projects\Router_api")
