import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

for fname in ['E:/Projects/Router_api/README.md', 'E:/Projects/Router_api/install_all.sh']:
    try:
        with open(fname, 'r', encoding='utf-8') as f:
            print(f"=== {fname} ===")
            print(f.read())
    except Exception as e:
        print(f"Error reading {fname}: {e}")
