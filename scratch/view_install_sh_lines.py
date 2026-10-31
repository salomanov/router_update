import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r'E:\Projects\Router_api\install.sh', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("Lines 65-75:")
for i in range(64, 76):
    if i < len(lines):
        print(f"{i+1}: {lines[i].rstrip()}")

print("\nLines 120-140:")
for i in range(119, 142):
    if i < len(lines):
        print(f"{i+1}: {lines[i].rstrip()}")
