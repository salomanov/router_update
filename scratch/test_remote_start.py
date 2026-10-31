import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect('178.140.8.56', port=34222, username='root', password='keenetic', timeout=10)

    commands = [
        "tail -n 40 /opt/var/log/router_api.log",
        "/opt/bin/python3 /opt/scripts/router_api.py"
    ]

    print("=== Last lines of /opt/var/log/router_api.log ===")
    stdin, stdout, stderr = client.exec_command("tail -n 40 /opt/var/log/router_api.log")
    print(stdout.read().decode('utf-8', errors='replace'))

    print("\n=== Direct run /opt/bin/python3 /opt/scripts/router_api.py ===")
    stdin, stdout, stderr = client.exec_command("timeout 5 /opt/bin/python3 /opt/scripts/router_api.py")
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print("STDOUT:\n", out)
    print("STDERR:\n", err)

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
