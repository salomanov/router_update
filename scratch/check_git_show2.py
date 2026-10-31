import sys
import subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

res = subprocess.run(["git", "-C", "E:\\Projects\\Router_api", "show", "7b927b0"], capture_output=True, text=True)
print(res.stdout[:2000])
