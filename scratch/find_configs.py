import sys
import glob

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

for fpath in glob.glob("E:/Projects/Router_api/**/*nfqws*", recursive=True):
    print(fpath)

for fpath in glob.glob("E:/Projects/Router_api/**/*conf*", recursive=True):
    print(fpath)
