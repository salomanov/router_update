import sys
import subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

cmd = ["git", "-C", "E:\\Projects\\Router_api", "log", "dc4bf80..HEAD", "--stat"]
res = subprocess.run(cmd, capture_output=True, text=True)
print("Commits by second agent:\n", res.stdout)
