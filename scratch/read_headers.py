import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r'E:\Projects\Router_api\AGENT_RECOMMENDATIONS.md', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
# Print outline (headers)
for i, l in enumerate(lines):
    if l.startswith('#'):
        print(f"Line {i+1}: {l.rstrip()}")
