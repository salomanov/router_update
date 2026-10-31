import sys
import shutil

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r'E:\Projects\Router_api\router_api.py', 'r', encoding='utf-8') as f:
    code = f.read()

target = """        search_paths = [
            os.path.join("/opt/share/www", filename),
            os.path.join(os.getcwd(), filename),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        ]"""

replacement = """        search_paths = [
            os.path.join("/opt/share/router-control-center", filename),
            os.path.join("/opt/share/www", filename),
            os.path.join(os.getcwd(), filename),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        ]"""

if target in code:
    code = code.replace(target, replacement)
    with open(r'E:\Projects\Router_api\router_api.py', 'w', encoding='utf-8', newline='\n') as f:
        f.write(code)
    shutil.copyfile(r'E:\Projects\Router_api\router_api.py', r'C:\Users\Salomanov\Desktop\Роутер\router_api.py')
    print("router_api.py updated successfully!")
else:
    print("Target not found in router_api.py")
