import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("Connecting to OUR local router 192.168.1.1:222...")
    client.connect('192.168.1.1', port=222, username='root', password='keenetic', timeout=10)

    # 1. Upload router_api.py
    with open(r'E:\Projects\Router_api\router_api.py', 'r', encoding='utf-8') as f:
        router_api_code = f.read()

    stdin, stdout, stderr = client.exec_command("cat > /opt/scripts/router_api.py")
    stdin.write(router_api_code)
    stdin.channel.shutdown_write()
    print("router_api.py write status:", stdout.channel.recv_exit_status())

    # 2. Upload latest index.html, app.js, style.css to /opt/share/router-control-center
    for fname in ['index.html', 'app.js', 'style.css']:
        with open(rf'E:\Projects\Router_api\{fname}', 'r', encoding='utf-8') as f:
            content = f.read()
        stdin, stdout, stderr = client.exec_command(f"cat > /opt/share/router-control-center/{fname}")
        stdin.write(content)
        stdin.channel.shutdown_write()
        print(f"{fname} write status:", stdout.channel.recv_exit_status())

    # 3. Restart S90router-api
    stdin, stdout, stderr = client.exec_command("/opt/etc/init.d/S90router-api restart")
    print("Restart output:\n", stdout.read().decode('utf-8', errors='replace'))

    # 4. Test curl on port 8089
    stdin, stdout, stderr = client.exec_command("curl -s -I http://127.0.0.1:8089/")
    print("Port 8089 HEAD response:\n", stdout.read().decode('utf-8', errors='replace'))

    stdin, stdout, stderr = client.exec_command("curl -s http://127.0.0.1:8089/ | head -n 10")
    print("Port 8089 GET body preview:\n", stdout.read().decode('utf-8', errors='replace'))

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
