import sys
import asyncio
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="msedge")
        page = await browser.new_page()

        page.on("console", lambda msg: print(f"[CONSOLE {msg.type}] {msg.text}"))
        def handle_response(response):
            if "index.php" in response.url:
                print(f"[HTTP {response.status}] {response.request.method} {response.url} -> post_data={response.request.post_data}")

        page.on("response", handle_response)

        await page.goto("http://192.168.1.1:90/", wait_until="networkidle")

        user_input = await page.query_selector("input[type='text'], input:not([type='password'])")
        pass_input = await page.query_selector("input[type='password']")
        if user_input and pass_input:
            await user_input.fill("root")
            await pass_input.fill("keenetic")
            submit_btn = await page.query_selector("button:has-text('Вход'), button[type='submit']")
            await submit_btn.click()
            await page.wait_for_timeout(2000)

        # Let's see the Save button status
        save_btn = await page.query_selector("button:has-text('Сохранить')")
        if save_btn:
            disabled = await save_btn.is_disabled()
            print(f"Save button disabled? {disabled}")

        # Let's check what the restart service button or status indicator shows
        # Look at the status icon: in screenshot 10, there's a green dot next to KEENETIC NFQWS 2
        # Let's check the restart button
        restart_btn = await page.query_selector("button[title*='Перезапуск'], [aria-label*='restart'], [aria-label*='Перезапуск']")
        print(f"Restart button found? {restart_btn is not None}")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
