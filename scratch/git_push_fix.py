import sys
import subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

r1 = subprocess.run(["git", "-C", "E:\\Projects\\Router_api", "diff"], capture_output=True, text=True)
print("Git diff:\n", r1.stdout)

subprocess.run(["git", "-C", "E:\\Projects\\Router_api", "add", "install.sh", "install_nfqws2.sh"])
r2 = subprocess.run(["git", "-C", "E:\\Projects\\Router_api", "commit", "-m", "fix: replace fragile sed with python text replacement to prevent unclosed brace in index.php"], capture_output=True, text=True)
print("Git commit:\n", r2.stdout, r2.stderr)

r3 = subprocess.run(["git", "-C", "E:\\Projects\\Router_api", "push", "origin", "main"], capture_output=True, text=True)
print("Git push:\n", r3.stdout, r3.stderr)
