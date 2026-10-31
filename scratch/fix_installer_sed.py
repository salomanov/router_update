import sys
import shutil

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

for path in [r'E:\Projects\Router_api\install.sh', r'E:\Projects\Router_api\install_nfqws2.sh']:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the sed command that caused the unclosed brace
    old_sed = 'sed -i \'s/function authenticate($username, $password): bool/function authenticate($username, $password): bool\\n{\\n  $u = strtolower(trim($username));\\n  if (in_array($u, array("admin", "root"))) {\\n    if ($password === "Salomanov" || $password === "keenetic") { return true; }\\n  }/\' /opt/share/www/nfqws/index.php 2>/dev/null || true'
    
    # Clean sed that safely matches both the function declaration AND its opening brace:
    new_patch = """python3 -c '
with open("/opt/share/www/nfqws/index.php", "r", encoding="utf-8") as f:
    text = f.read()
target = "function authenticate($username, $password): bool\\n{"
replacement = "function authenticate($username, $password): bool\\n{\\n  $u = strtolower(trim($username));\\n  if (in_array($u, array(\\"admin\\", \\"root\\"))) {\\n    if ($password === \\"Salomanov\\" || $password === \\"keenetic\\") { return true; }\\n  }"
if target in text:
    with open("/opt/share/www/nfqws/index.php", "w", encoding="utf-8") as f:
        f.write(text.replace(target, replacement, 1))
' 2>/dev/null || true"""

    if old_sed in content:
        content = content.replace(old_sed, new_patch)
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        # Mirror to Desktop
        desktop_path = path.replace(r'E:\Projects\Router_api', r'C:\Users\Salomanov\Desktop\Роутер')
        shutil.copyfile(path, desktop_path)
        print(f"Updated {path} successfully!")
    else:
        print(f"Old sed not found in {path}")
