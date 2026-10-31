import sys
import os
import shutil

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

gemini_skill_dir = r"C:\Users\Salomanov\.gemini\config\skills\project-guardian"
e_skill_dir = r"E:\Projects\Skill"

if os.path.exists(gemini_skill_dir) and os.path.exists(e_skill_dir):
    print("Both directories exist. Syncing E:\\Projects\\Skill to ~/.gemini/config/skills/project-guardian...")
    for root, dirs, files in os.walk(e_skill_dir):
        if '.git' in root or '__pycache__' in root:
            continue
        rel = os.path.relpath(root, e_skill_dir)
        target_dir = os.path.join(gemini_skill_dir, rel) if rel != '.' else gemini_skill_dir
        os.makedirs(target_dir, exist_ok=True)
        for f in files:
            src_f = os.path.join(root, f)
            dst_f = os.path.join(target_dir, f)
            shutil.copy2(src_f, dst_f)
    print("Sync completed!")
else:
    print(f"Paths check: gemini={os.path.exists(gemini_skill_dir)}, e={os.path.exists(e_skill_dir)}")
