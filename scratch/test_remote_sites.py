import paramiko
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

HOST = "178.140.8.56"
PORT = 34222
USER = "root"
PASS = "keenetic"

DOMAINS = [
    # Video & Media
    ("YouTube", "https://www.youtube.com"),
    ("YouTube Images (i.ytimg.com)", "https://i.ytimg.com/generate_204"),
    ("Google Video (GGC)", "https://redirector.googlevideo.com/report_mapping"),
    
    # Messengers & Social
    ("Discord Web", "https://discord.com"),
    ("Discord API Gateway", "https://gateway.discord.gg"),
    ("Instagram", "https://www.instagram.com"),
    ("X (Twitter)", "https://x.com"),
    ("Facebook", "https://www.facebook.com"),
    ("Telegram Web", "https://web.telegram.org"),
    
    # Torrents & Libraries
    ("Rutracker", "https://rutracker.org"),
    ("NNMClub", "https://nnmclub.to"),
    ("Kinozal", "https://kinozal.tv"),
    ("Flibusta", "https://flibusta.is"),
    
    # AI & Services
    ("ChatGPT", "https://chatgpt.com"),
    ("OpenAI API", "https://api.openai.com"),
    
    # Russian sites (Verify no breakdown)
    ("Yandex", "https://ya.ru"),
    ("VKontakte", "https://vk.com"),
    ("Gosuslugi", "https://www.gosuslugi.ru")
]

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to remote router {HOST}:{PORT}...")
    client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

    # First check nfqws2 cmdline
    print("\n--- NFQWS2 process arguments ---")
    stdin, stdout, stderr = client.exec_command("tr '\\0' ' ' < /proc/$(pidof nfqws2)/cmdline; echo")
    cmdline = stdout.read().decode('utf-8', errors='replace').strip()
    print(cmdline)

    results = []
    print("\n--- Testing Target Websites ---")
    format_str = "{:<25} | {:<40} | {:<10} | {:<10} | {:<12}"
    print(format_str.format("Service", "URL", "HTTP Code", "Total Time", "Status"))
    print("-" * 105)

    for name, url in DOMAINS:
        # Run curl on router: returns http_code, time_total, time_connect, time_appconnect (TLS)
        # format: '%{http_code}|%{time_total}|%{time_appconnect}|%{remote_ip}\n'
        curl_cmd = (
            f"curl -k -s -o /dev/null -w '%{{http_code}}|%{{time_total}}|%{{time_appconnect}}|%{{remote_ip}}' "
            f"--connect-timeout 6 --max-time 10 '{url}'"
        )
        stdin, stdout, stderr = client.exec_command(curl_cmd, timeout=15)
        raw = stdout.read().decode('utf-8', errors='replace').strip()
        err = stderr.read().decode('utf-8', errors='replace').strip()

        if "|" in raw:
            parts = raw.split("|")
            http_code = parts[0]
            total_time = f"{float(parts[1]):.2f}s" if parts[1] else "-"
            tls_time = f"{float(parts[2]):.2f}s" if parts[2] else "-"
            remote_ip = parts[3] if len(parts) > 3 else "-"
            
            if http_code in ("200", "204", "301", "302", "307", "308", "403", "404", "400", "405"):
                status = "OK (Работает)"
            elif http_code == "000":
                status = "TIMEOUT/BLOCKED"
            else:
                status = f"CODE {http_code}"
        else:
            http_code = "ERR"
            total_time = "-"
            status = "FAILED: " + (err[:20] if err else raw[:20])

        print(format_str.format(name[:25], url[:40], http_code, total_time, status))
        results.append({
            "name": name,
            "url": url,
            "code": http_code,
            "time": total_time,
            "status": status
        })

    client.close()

if __name__ == "__main__":
    main()
