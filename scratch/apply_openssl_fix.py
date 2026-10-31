import sys
import shutil

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 1. Update install.sh
with open(r'E:\Projects\Router_api\install.sh', 'r', encoding='utf-8') as f:
    sh_text = f.read()

old_deps = 'DEPS="python3-light python3-email python3-logging python3-urllib python3-codecs python3-idna curl wget-ssl ca-certificates ca-bundle"'
new_deps = 'DEPS="python3-light python3-openssl python3-email python3-logging python3-urllib python3-codecs python3-idna curl wget-ssl ca-certificates ca-bundle"'

if old_deps in sh_text:
    sh_text = sh_text.replace(old_deps, new_deps)
    with open(r'E:\Projects\Router_api\install.sh', 'w', encoding='utf-8', newline='\n') as f:
        f.write(sh_text)
    shutil.copy2(r'E:\Projects\Router_api\install.sh', r'C:\Users\Salomanov\Desktop\Роутер\install.sh')
    print("install.sh updated with python3-openssl!")
else:
    print("old_deps not found in install.sh")

# 2. Update router_api.py with PBKDF2 fallback
with open(r'E:\Projects\Router_api\router_api.py', 'r', encoding='utf-8') as f:
    py_text = f.read()

old_hash = """def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS
    ).hex()
    return salt, hashed"""

new_hash = """def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    if hasattr(hashlib, "pbkdf2_hmac"):
        hashed = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS
        ).hex()
    else:
        import hmac
        pwd_bytes = password.encode("utf-8")
        salt_bytes = salt.encode("utf-8")
        u = hmac.new(pwd_bytes, salt_bytes + b"\\x00\\x00\\x00\\x01", hashlib.sha256).digest()
        t = bytearray(u)
        for _ in range(1, PBKDF2_ITERATIONS):
            u = hmac.new(pwd_bytes, u, hashlib.sha256).digest()
            for j in range(32):
                t[j] ^= u[j]
        hashed = bytes(t).hex()
    return salt, hashed"""

if old_hash in py_text:
    py_text = py_text.replace(old_hash, new_hash)
    with open(r'E:\Projects\Router_api\router_api.py', 'w', encoding='utf-8', newline='\n') as f:
        f.write(py_text)
    shutil.copy2(r'E:\Projects\Router_api\router_api.py', r'C:\Users\Salomanov\Desktop\Роутер\router_api.py')
    print("router_api.py updated with robust fallback!")
else:
    print("old_hash not found in router_api.py")
