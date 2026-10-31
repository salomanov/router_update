import sys
import asyncio
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="msedge")
        page = await browser.new_page()

        errors = []
        page.on("console", lambda msg: errors.append(f"[CONSOLE {msg.type}] {msg.text}") if msg.type in ['error', 'warning'] else None)
        page.on("pageerror", lambda exc: errors.append(f"[PAGE ERROR] {exc}"))

        def handle_response(response):
            if response.status >= 400:
                errors.append(f"[HTTP {response.status}] {response.request.method} {response.url}")

        page.on("response", handle_response)

        print("1. Opening http://192.168.1.1:90/ ...")
        await page.goto("http://192.168.1.1:90/", wait_until="networkidle")

        # Check if login form is present
        user_input = await page.query_selector("input[type='text'], input:not([type='password'])")
        pass_input = await page.query_selector("input[type='password']")
        if user_input and pass_input:
            print("Login form is shown. Logging in with root:keenetic...")
            await user_input.fill("root")
            await pass_input.fill("keenetic")
            submit_btn = await page.query_selector("button:has-text('Вход'), button[type='submit']")
            await submit_btn.click()
            await page.wait_for_timeout(2000)

        # Now we are inside! Let's check tabs
        print("Checking tabs and contents...")
        tabs = ["Настройки", "Списки", "Логи", "Скрипты"]
        for tab in tabs:
            btn = await page.query_selector(f"button:has-text('{tab}'), a:has-text('{tab}'), div:has-text('{tab}')")
            if btn:
                print(f"Clicking tab '{tab}'...")
                await btn.click()
                await page.wait_for_timeout(1000)
                shot_name = f"tab_{tab}.png"
                await page.screenshot(path=rf"C:\Users\Salomanov\.gemini\antigravity\brain\69ccc142-f237-439d-bcb7-bba5087ae205\{shot_name}")
                print(f"Saved screenshot {shot_name}")

        # Let's test "Проверить домены" button
        check_btn = await page.query_selector("button:has-text('Проверить домены')")
        if check_btn:
            print("Clicking 'Проверить домены'...")
            await check_btn.click()
            await page.wait_for_timeout(3000)
            await page.screenshot(path=r"C:\Users\Salomanov\.gemini\antigravity\brain\69ccc142-f237-439d-bcb7-bba5087ae205\check_domains.png")

        print("\nAll logged errors / warnings:")
        for err in errors:
            print(err)

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
