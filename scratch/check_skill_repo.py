import sys
import subprocess
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

if os.path.exists(r'E:\Projects\Skill'):
    cmd = ["git", "-C", "E:\\Projects\\Skill", "log", "-n", "5", "--oneline"]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    print("Git log in E:\\Projects\\Skill:\n", res.stdout)
    
    cmd2 = ["git", "-C", "E:\\Projects\\Skill", "status"]
    res2 = subprocess.run(cmd2, capture_output=True, text=True, encoding='utf-8', errors='replace')
    print("Git status in E:\\Projects\\Skill:\n", res2.stdout)
else:
    print("E:\\Projects\\Skill does not exist")
