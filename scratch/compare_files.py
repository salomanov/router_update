import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

repo_dir = r"E:\Projects\Router_api"
desktop_dir = r"c:\Users\Salomanov\Desktop\Роутер"

files = ["app.js", "index.html", "style.css", "router_api.py", "PROJECT_STATE.md", "README.md", "install.sh", "install_all.sh", "install_nfqws2.sh", "S90router-api"]

print("Comparing files between E:\\Projects\\Router_api and Desktop\\Роутер:")
for f in files:
    p1 = os.path.join(repo_dir, f)
    p2 = os.path.join(desktop_dir, f)
    if os.path.exists(p1) and os.path.exists(p2):
        s1 = os.path.getsize(p1)
        s2 = os.path.getsize(p2)
        diff = "IDENTICAL" if open(p1, 'rb').read() == open(p2, 'rb').read() else f"DIFFER (size {s1} vs {s2})"
        print(f"  {f}: {diff}")
    else:
        print(f"  {f}: p1_exists={os.path.exists(p1)}, p2_exists={os.path.exists(p2)}")
