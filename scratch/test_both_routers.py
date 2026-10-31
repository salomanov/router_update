import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def test_router(name, host, port, user, pwd):
    print(f"\n==========================================")
    print(f"Testing {name} ({host}:{port})...")
    print(f"==========================================")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        c.connect(host, port=port, username=user, password=pwd, timeout=10)
        
        # Test 8089 (GRouter)
        _, stdout, _ = c.exec_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8089/")
        code_8089 = stdout.read().decode('utf-8').strip()
        print(f"  [GRouter Port 8089] -> HTTP {code_8089}")
        
        # Test 90 (nfqws-web)
        _, stdout, _ = c.exec_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:90/")
        code_90 = stdout.read().decode('utf-8').strip()
        print(f"  [nfqws Web Port 90] -> HTTP {code_90}")
        
        # Test nfqws-web API
        _, stdout, _ = c.exec_command("curl -s -X POST -d 'cmd=status' http://127.0.0.1:90/index.php")
        status_json = stdout.read().decode('utf-8').strip()
        print(f"  [nfqws Web API]     -> {status_json}")
        
        # Test nfqws service running
        _, stdout, _ = c.exec_command("ps | grep -E 'nfqws2|lighttpd|router_api' | grep -v grep")
        procs = stdout.read().decode('utf-8').strip().splitlines()
        print(f"  [Active Processes]  -> {len(procs)} processes running")
        for p in procs:
            print(f"     * {p.strip()}")
            
    except Exception as e:
        print(f"  Error on {name}: {e}")
    finally:
        c.close()

# 1. OUR local router
test_router("НАШ ЛОКАЛЬНЫЙ РОУТЕР", "192.168.1.1", 222, "root", "keenetic")

# 2. REMOTE router
test_router("УДАЛЕННЫЙ РОУТЕР", "178.140.8.56", 34222, "root", "keenetic")
