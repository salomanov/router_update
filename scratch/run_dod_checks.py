import sys
import subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

cwd = r"E:\Projects\Router_api"

print("1. Python compile check:")
r1 = subprocess.run(["python", "-m", "py_compile", "router_api.py", "opkg_update.py", "mock_router_api.py", "grouter_cli.py"], cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
print("  Exit code:", r1.returncode)
if r1.stderr: print("  Stderr:", r1.stderr)

print("2. Node syntax check:")
r2 = subprocess.run(["node", "--check", "app.js"], cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
print("  Exit code:", r2.returncode)
if r2.stderr: print("  Stderr:", r2.stderr)

print("3. Bash scripts syntax check (via Git bash):")
bash_path = r"C:\Program Files\Git\bin\bash.exe"
r3 = subprocess.run([bash_path, "-c", "sh -n install.sh && sh -n install_all.sh && sh -n install_nfqws2.sh && sh -n install_tailscale.sh"], cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
print("  Exit code:", r3.returncode)
if r3.stderr: print("  Stderr:", r3.stderr)
