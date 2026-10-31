import sys
import subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

cwd = r"E:\Projects\Router_api"

subprocess.run(["git", "-C", cwd, "add", "install.sh", "router_api.py"])
r1 = subprocess.run(["git", "-C", cwd, "commit", "-m", "fix: add python3-openssl to install dependencies and add pure-python pbkdf2 fallback"], capture_output=True, text=True, encoding='utf-8', errors='replace')
print("Commit:\n", r1.stdout, r1.stderr)

r2 = subprocess.run(["git", "-C", cwd, "push", "origin", "main"], capture_output=True, text=True, encoding='utf-8', errors='replace')
print("Push:\n", r2.stdout, r2.stderr)
