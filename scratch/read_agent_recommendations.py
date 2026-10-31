import sys
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Read AGENT_RECOMMENDATIONS.md
with open(r'E:\Projects\Router_api\AGENT_RECOMMENDATIONS.md', 'r', encoding='utf-8', errors='replace') as f:
    text = f.read()

print("=== AGENT_RECOMMENDATIONS.md (first 3000 chars) ===")
print(text[:3000])

print("\n=== AGENT_RECOMMENDATIONS.md (last 3000 chars) ===")
print(text[-3000:])
