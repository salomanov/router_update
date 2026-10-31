import sys
import subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

res = subprocess.run(["git", "-C", "E:\\Projects\\Router_api", "diff"], capture_output=True, text=True)
print(res.stdout)
