import sys
import subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

r1 = subprocess.run(["git", "-C", "E:\\Projects\\Router_api", "status"], capture_output=True, text=True, encoding='utf-8', errors='replace')
print("Status Router_api:\n", r1.stdout)

r2 = subprocess.run(["git", "-C", "E:\\Projects\\Skill", "status"], capture_output=True, text=True, encoding='utf-8', errors='replace')
print("Status Skill:\n", r2.stdout)
