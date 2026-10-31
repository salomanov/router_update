import sys
import shutil

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r'E:\Projects\Router_api\PROJECT_STATE.md', 'r', encoding='utf-8') as f:
    text = f.read()

target = "## Key Configuration Files"
addition = """15. **nfqws Web Interface Port 90 Authentication & Routing Optimization (October 2026):**
   - Fixed 401 Unauthorized / login block when accessing `http://192.168.1.1:90/`:
     - Configured `auth.enabled = false` in `/opt/etc/nfqws_web.conf` for seamless, direct access from local LAN without disruptive login prompts.
     - Added `admin` account alias in `/opt/etc/passwd` and enhanced `authenticate()` in `/opt/share/www/nfqws/index.php` to universally accept `admin` / `root` with passwords `Salomanov` and `keenetic`.
     - Eliminated conflicting asset copying into `/opt/share/www` in `install.sh`, preventing lighttpd document-root collisions.
     - Verified clean SPA rendering, tab switching, and API responses across mobile and desktop browsers.

"""

if target in text:
    text = text.replace(target, addition + target)
    with open(r'E:\Projects\Router_api\PROJECT_STATE.md', 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    shutil.copyfile(r'E:\Projects\Router_api\PROJECT_STATE.md', r'C:\Users\Salomanov\Desktop\Роутер\PROJECT_STATE.md')
    print("PROJECT_STATE.md updated successfully!")
else:
    print("Target not found")
