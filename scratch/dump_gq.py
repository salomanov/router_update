import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect('192.168.1.1', port=222, username='root', password='keenetic', timeout=10)

    # Let's inspect where GQ is defined in index.DaPMM2qc.js
    cmd = """python3 -c "
with open('/opt/share/www/nfqws/assets/index.DaPMM2qc.js', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

idx = text.find('GQ={')
if idx != -1:
    print('Found GQ at', idx)
    print(text[idx:idx+1500])
else:
    print('GQ not found')
" """
    stdin, stdout, stderr = client.exec_command(cmd)
    print(stdout.read().decode('utf-8', errors='replace'))

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
