import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

paths = [
    r"c:\Users\Salomanov\Desktop\Роутер\PROJECT_STATE.md",
    r"E:\Projects\Router_api\PROJECT_STATE.md",
    r"c:\Users\Salomanov\Desktop\Роутер\README.md",
    r"E:\Projects\Router_api\README.md"
]

for p in paths:
    if os.path.exists(p):
        print(f"=== Found {p} ===")
        with open(p, 'r', encoding='utf-8', errors='replace') as f:
            print(f.read()[:1500])
    else:
        print(f"Not found: {p}")
