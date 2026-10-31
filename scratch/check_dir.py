import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

print("Current working dir:", os.getcwd())
if os.path.exists("E:\\Projects\\Router_api"):
    print("E:\\Projects\\Router_api exists! Contents:", os.listdir("E:\\Projects\\Router_api"))
else:
    print("E:\\Projects\\Router_api does not exist!")

if os.path.exists("."):
    print("Current dir contents:", os.listdir("."))
