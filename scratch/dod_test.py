import sys
import subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

cwd = r"E:\Projects\Router_api"
r1 = subprocess.run(["python", "-m", "py_compile", "router_api.py"], cwd=cwd, capture_output=True, text=True)
print("py_compile code:", r1.returncode)

bash_path = r"C:\Program Files\Git\bin\bash.exe"
r2 = subprocess.run([bash_path, "-c", "sh -n install.sh"], cwd=cwd, capture_output=True, text=True)
print("sh -n code:", r2.returncode)
