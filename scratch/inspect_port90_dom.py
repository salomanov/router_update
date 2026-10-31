import sys
import asyncio
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="msedge")
        page = await browser.new_page()

        await page.goto("http://192.168.1.1:90/", wait_until="networkidle")

        user_input = await page.query_selector("input[type='text'], input:not([type='password'])")
        pass_input = await page.query_selector("input[type='password']")
        if user_input and pass_input:
            await user_input.fill("root")
            await pass_input.fill("keenetic")
            submit_btn = await page.query_selector("button:has-text('Вход'), button[type='submit']")
            await submit_btn.click()
            await page.wait_for_timeout(2000)

        # Inspect the navigation links/buttons
        links = await page.eval_on_selector_all(
            "header a, nav a, [role='tab'], button",
            "els => els.map(e => ({ tag: e.tagName, text: e.innerText, href: e.getAttribute('href'), role: e.getAttribute('role'), class: e.className }))"
        )
        for l in links:
            if any(k in l['text'] for k in ['Настройки', 'Списки', 'Логи', 'Скрипты']):
                print(l)

        # Let's try clicking specifically on the "Списки" tab
        spiski = await page.get_by_text("Списки", exact=True).all()
        print(f"Found {len(spiski)} elements with exact text 'Списки'")
        for i, s in enumerate(spiski):
            tag = await s.evaluate("e => e.tagName")
            vis = await s.is_visible()
            print(f"  {i}: <{tag}> visible={vis}")
            if vis:
                await s.click()
                await page.wait_for_timeout(1500)
                await page.screenshot(path=r"C:\Users\Salomanov\.gemini\antigravity\brain\69ccc142-f237-439d-bcb7-bba5087ae205\spiski_clicked.png")
                print("Clicked and saved spiski_clicked.png")
                break

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
