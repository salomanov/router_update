import sys
import subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

r = subprocess.run(["git", "-C", "E:\\Projects\\Router_api", "log", "-n", "12", "--oneline"], capture_output=True, text=True)
print("Git log in E:\\Projects\\Router_api:")
print(r.stdout)

r2 = subprocess.run(["git", "-C", "E:\\Projects\\Router_api", "status"], capture_output=True, text=True)
print("\nGit status in E:\\Projects\\Router_api:")
print(r2.stdout)
