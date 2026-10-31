import sys
import subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

res = subprocess.run(["git", "-C", "E:\\Projects\\Router_api", "show", "927c24e"], capture_output=True, text=True)
print(res.stdout[:2000])
