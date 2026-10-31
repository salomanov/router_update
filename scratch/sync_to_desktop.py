import sys
import shutil
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

src_dir = r"E:\Projects\Router_api"
dst_dir = r"c:\Users\Salomanov\Desktop\Роутер"

synced = []
for fname in os.listdir(src_dir):
    if fname in ['.git', 'scratch', '__pycache__', 'node_modules', 'downloads', 'graphify-out', 'ChatExport_2026-08-22', 'ses_e7de4ad6effdc1tpqZ6K3gVufy.json']:
        continue
    src_file = os.path.join(src_dir, fname)
    dst_file = os.path.join(dst_dir, fname)
    if os.path.isfile(src_file):
        shutil.copy2(src_file, dst_file)
        synced.append(fname)
    elif os.path.isdir(src_file) and fname == 'configs':
        shutil.copytree(src_file, dst_file, dirs_exist_ok=True)
        synced.append(fname + '/')

print(f"Synced {len(synced)} items to Desktop directory: {synced}")
