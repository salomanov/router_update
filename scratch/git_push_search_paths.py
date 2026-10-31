import sys
import subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

r1 = subprocess.run(["git", "-C", "E:\\Projects\\Router_api", "diff"], capture_output=True, text=True)
print("Git diff:\n", r1.stdout)

subprocess.run(["git", "-C", "E:\\Projects\\Router_api", "add", "router_api.py", "PROJECT_STATE.md"])
r2 = subprocess.run(["git", "-C", "E:\\Projects\\Router_api", "commit", "-m", "fix(router-api): prioritize /opt/share/router-control-center in search_paths for static files"], capture_output=True, text=True)
print("Git commit:\n", r2.stdout, r2.stderr)

r3 = subprocess.run(["git", "-C", "E:\\Projects\\Router_api", "push", "origin", "main"], capture_output=True, text=True)
print("Git push:\n", r3.stdout, r3.stderr)
