import paramiko
import sys
import json
import time

sys.stdout.reconfigure(encoding='utf-8')

HOST = "178.140.8.56"
PORT = 34222
USER = "root"
PASS = "keenetic"

def run_ssh(commands):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {HOST}:{PORT}...")
    client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
    
    results = {}
    for name, cmd in commands.items():
        print(f"\n--- Running: {name} ({cmd}) ---")
        stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
        out = stdout.read().decode('utf-8', errors='replace')
        err = stderr.read().decode('utf-8', errors='replace')
        print(f"STDOUT:\n{out}")
        if err.strip():
            print(f"STDERR:\n{err}")
        results[name] = {"out": out, "err": err}
    
    client.close()
    return results

if __name__ == "__main__":
    cmds = {
        "iptables_mangle": "iptables -t mangle -S",
        "nfqws_conf": "cat /opt/etc/nfqws2/nfqws2.conf",
        "nfqws_status": "/opt/etc/init.d/S51nfqws2 status",
        "nfqws_log": "tail -n 40 /opt/var/log/nfqws2.log",
        "check_script_locations": "ls -la /opt/etc/nfqws2/ /opt/share/www/nfqws/scripts/ 2>/dev/null",
        "curl_check_router": "curl -svo /dev/null --connect-timeout 5 https://www.youtube.com 2>&1 | head -n 25",
        "curl_check_googlevideo": "curl -svo /dev/null --connect-timeout 5 https://rr1---sn-axq7sn7z.googlevideo.com 2>&1 | head -n 25",
        "curl_check_discord": "curl -svo /dev/null --connect-timeout 5 https://discord.com 2>&1 | head -n 25"
    }
    run_ssh(cmds)
