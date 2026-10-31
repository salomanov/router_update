import sys
import subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add modified files
r1 = subprocess.run(["git", "-C", "E:\\Projects\\Router_api", "add", "install.sh", "install_nfqws2.sh", "PROJECT_STATE.md"], capture_output=True, text=True)
print("git add:", r1.stdout, r1.stderr)

# Commit
commit_msg = "fix(nfqws-web): disable mandatory auth on LAN, support admin/root credentials, and prevent lighttpd file collisions"
r2 = subprocess.run(["git", "-C", "E:\\Projects\\Router_api", "commit", "-m", commit_msg], capture_output=True, text=True)
print("git commit:", r2.stdout, r2.stderr)

# Push
r3 = subprocess.run(["git", "-C", "E:\\Projects\\Router_api", "push", "origin", "main"], capture_output=True, text=True)
print("git push:", r3.stdout, r3.stderr)
