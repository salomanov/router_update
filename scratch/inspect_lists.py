import paramiko
import sys

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
        print(f"\n=================== {name} ===================")
        print(f"COMMAND: {cmd}")
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
        "ps_nfqws2": "ps -w | grep nfqws2 | grep -v grep",
        "nfqws2_conf_run": "cat /opt/etc/nfqws2/nfqws2.conf.run",
        "lists_dir": "ls -lh /opt/etc/nfqws2/lists/",
        "user_list": "head -n 40 /opt/etc/nfqws2/lists/user.list",
        "user_list_count": "wc -l /opt/etc/nfqws2/lists/*.list",
        "auto_list": "head -n 40 /opt/etc/nfqws2/lists/auto.list",
        "grep_user_google": "grep -i 'googlevideo\\|youtube\\|discord\\|rutracker\\|instagram' /opt/etc/nfqws2/lists/user.list",
        "grep_auto_google": "grep -i 'googlevideo\\|youtube\\|discord\\|rutracker\\|instagram' /opt/etc/nfqws2/lists/auto.list"
    }
    run_ssh(cmds)
