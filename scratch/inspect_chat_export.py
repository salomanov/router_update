import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

path = r"E:\Projects\Router_api\ChatExport_2026-10-31"

if os.path.exists(path):
    if os.path.isdir(path):
        print(f"Path is directory: {path}")
        entries = os.listdir(path)
        for e in entries:
            full_p = os.path.join(path, e)
            sz = os.path.getsize(full_p) if os.path.isfile(full_p) else "DIR"
            print(f"  {e} ({sz})")
    else:
        print(f"Path is file: {path} (size {os.path.getsize(path)})")
else:
    print(f"Path not found: {path}")
    parent = r"E:\Projects\Router_api"
    if os.path.exists(parent):
        print(f"Parent directory listing {parent}:")
        for e in os.listdir(parent):
            if "chat" in e.lower() or "export" in e.lower() or "2026" in e.lower():
                print(f"  {e}")
