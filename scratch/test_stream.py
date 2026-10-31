import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')

HOST = "178.140.8.56"
PORT = 34222
USER = "root"
PASS = "keenetic"

def run_yt_stream_test():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
    
    # Test downloading a sample YouTube googlevideo manifest or test endpoint
    cmd = """
    echo "=== 1. YouTube Web ==="
    curl -I -s --connect-timeout 5 https://www.youtube.com | head -n 5
    
    echo "=== 2. Discord CDN ==="
    curl -I -s --connect-timeout 5 https://cdn.discordapp.com | head -n 5
    
    echo "=== 3. Instagram Web ==="
    curl -I -s --connect-timeout 5 https://www.instagram.com | head -n 5
    
    echo "=== 4. Rutracker Forum ==="
    curl -I -s --connect-timeout 5 https://rutracker.org | head -n 5
    
    echo "=== 5. NFQWS2 Log (Latest 15 events) ==="
    tail -n 15 /opt/var/log/nfqws2.log
    """
    stdin, stdout, stderr = client.exec_command(cmd)
    print(stdout.read().decode('utf-8', errors='replace'))
    client.close()

if __name__ == "__main__":
    run_yt_stream_test()
