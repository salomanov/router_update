import sys
import subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

cmd = ["git", "-C", "E:\\Projects\\Router_api", "show", "94d70e4", "--stat"]
res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
print("Status of 94d70e4:\n", res.stdout)

cmd2 = ["git", "-C", "E:\\Projects\\Router_api", "show", "-s", "94d70e4"]
res2 = subprocess.run(cmd2, capture_output=True, text=True, encoding='utf-8', errors='replace')
print("\nCommit message of 94d70e4:\n", res2.stdout)
