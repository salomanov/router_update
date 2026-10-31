import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r'E:\Projects\Router_api\PROJECT_STATE.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines in PROJECT_STATE.md: {len(lines)}")
for l in lines[-40:]:
    print(l.rstrip())
