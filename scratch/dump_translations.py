import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect('192.168.1.1', port=222, username='root', password='keenetic', timeout=10)

    cmd = """python3 -c "
with open('/opt/share/www/nfqws/assets/index.DaPMM2qc.js', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

idx = text.find('GQ={')
print(text[idx-4000:idx])
" """
    stdin, stdout, stderr = client.exec_command(cmd)
    print(stdout.read().decode('utf-8', errors='replace'))

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
