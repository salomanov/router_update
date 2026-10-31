import sys
import paramiko
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect('192.168.1.1', port=222, username='root', password='keenetic', timeout=10)

    # Search for all strings with 'установ' in the web UI files
    cmd = """python3 -c "
import glob, re
for f in glob.glob('/opt/share/www/nfqws/assets/*.js'):
    with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
        c = fp.read()
        m = re.findall(r'[\"\\\'][^\"\\\']*?установ[^\"\\\']*?[\"\\\']', c, re.IGNORECASE)
        if m:
            print(f, m)
" """
    stdin, stdout, stderr = client.exec_command(cmd)
    print("Matches in assets:\n", stdout.read().decode('utf-8', errors='replace'))

    # Also check /opt/share/router-control-center
    cmd2 = """python3 -c "
import glob, re
for f in glob.glob('/opt/share/router-control-center/*.js'):
    with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
        c = fp.read()
        m = re.findall(r'[\"\\\'][^\"\\\']*?установ[^\"\\\']*?[\"\\\']', c, re.IGNORECASE)
        if m:
            print(f, m)
" """
    stdin, stdout, stderr = client.exec_command(cmd2)
    print("Matches in router-control-center:\n", stdout.read().decode('utf-8', errors='replace'))

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
