import urllib.request
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

print("=== Тестирование Google и сайтов на ЭТОМ ПК ===")

urls = [
    ("Google", "https://www.google.com"),
    ("Google (HTTP)", "http://www.google.com"),
    ("YouTube", "https://www.youtube.com"),
    ("Yandex", "https://ya.ru"),
    ("VK", "https://vk.com"),
    ("Telegram Web", "https://web.telegram.org")
]

for name, url in urls:
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            dt = (time.time() - t0) * 1000
            print(f"{name:<15} ({url}) -> OK {resp.status} за {dt:.1f} мс")
    except Exception as e:
        dt = (time.time() - t0) * 1000
        print(f"{name:<15} ({url}) -> СБОЙ ({dt:.1f} мс): {e}")
