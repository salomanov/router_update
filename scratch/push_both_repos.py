import sys
import subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 1. Check git status in E:\Projects\Router_api
r = subprocess.run(["git", "-C", "E:\\Projects\\Router_api", "status"], capture_output=True, text=True, encoding='utf-8', errors='replace')
print("Status E:\\Projects\\Router_api:\n", r.stdout)

# Add ses_*.json to .gitignore if needed, or check .gitignore
with open(r'E:\Projects\Router_api\.gitignore', 'r', encoding='utf-8') as f:
    gi = f.read()

if 'ses_*.json' not in gi and 'ses_' not in gi:
    with open(r'E:\Projects\Router_api\.gitignore', 'a', encoding='utf-8') as f:
        f.write('\nses_*.json\n*.sessions\n')
    subprocess.run(["git", "-C", "E:\\Projects\\Router_api", "add", ".gitignore"])
    subprocess.run(["git", "-C", "E:\\Projects\\Router_api", "commit", "-m", "chore: ignore session export json files"])
    print("Added ses_*.json to .gitignore and committed")

# 2. Push E:\Projects\Router_api
print("\nPushing E:\\Projects\\Router_api to origin main...")
push_r = subprocess.run(["git", "-C", "E:\\Projects\\Router_api", "push", "origin", "main"], capture_output=True, text=True, encoding='utf-8', errors='replace')
print("Push stdout:\n", push_r.stdout)
print("Push stderr:\n", push_r.stderr)
print("Push returncode:", push_r.returncode)

# 3. Check E:\Projects\Skill
print("\nChecking E:\\Projects\\Skill...")
skill_status = subprocess.run(["git", "-C", "E:\\Projects\\Skill", "status"], capture_output=True, text=True, encoding='utf-8', errors='replace')
print("Status E:\\Projects\\Skill:\n", skill_status.stdout)

print("\nPushing E:\\Projects\\Skill to origin main...")
skill_push = subprocess.run(["git", "-C", "E:\\Projects\\Skill", "push", "origin", "main"], capture_output=True, text=True, encoding='utf-8', errors='replace')
print("Skill push stdout:\n", skill_push.stdout)
print("Skill push stderr:\n", skill_push.stderr)
print("Skill push returncode:", skill_push.returncode)
