import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("Updating REMOTE router 178.140.8.56:34222...")
    client.connect('178.140.8.56', port=34222, username='root', password='keenetic', timeout=10)

    # 1. Upload updated router_api.py
    with open(r'E:\Projects\Router_api\router_api.py', 'r', encoding='utf-8') as f:
        router_api_code = f.read()

    stdin, stdout, stderr = client.exec_command("cat > /opt/scripts/router_api.py")
    stdin.write(router_api_code)
    stdin.channel.shutdown_write()
    print("Remote router_api.py write status:", stdout.channel.recv_exit_status())

    # 2. Upload latest index.html, app.js, style.css to /opt/share/router-control-center
    for fname in ['index.html', 'app.js', 'style.css']:
        with open(rf'E:\Projects\Router_api\{fname}', 'r', encoding='utf-8') as f:
            content = f.read()
        stdin, stdout, stderr = client.exec_command(f"cat > /opt/share/router-control-center/{fname}")
        stdin.write(content)
        stdin.channel.shutdown_write()
        print(f"Remote {fname} write status:", stdout.channel.recv_exit_status())

    # 3. Restart S90router-api on remote router
    stdin, stdout, stderr = client.exec_command("/opt/etc/init.d/S90router-api restart")
    print("Remote restart output:\n", stdout.read().decode('utf-8', errors='replace'))

    # 4. Verify HTTP code
    stdin, stdout, stderr = client.exec_command("sleep 1; curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8089/")
    print("Remote 8089 HTTP code:", stdout.read().decode('utf-8').strip())

    stdin, stdout, stderr = client.exec_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:90/")
    print("Remote 90 HTTP code:", stdout.read().decode('utf-8').strip())

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
