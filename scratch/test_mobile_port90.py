import sys
import asyncio
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="msedge")
        context = await browser.new_context(viewport={'width': 375, 'height': 812}, is_mobile=True)
        page = await context.new_page()

        print("Testing mobile viewport 375x812...")
        await page.goto("http://192.168.1.1:90/", wait_until="networkidle")

        screenshot_path = r"C:\Users\Salomanov\.gemini\antigravity\brain\69ccc142-f237-439d-bcb7-bba5087ae205\12_port_90_mobile_login.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"Mobile login screenshot: {screenshot_path}")

        user_input = await page.query_selector("input[type='text'], input:not([type='password'])")
        pass_input = await page.query_selector("input[type='password']")
        if user_input and pass_input:
            await user_input.fill("root")
            await pass_input.fill("keenetic")
            submit_btn = await page.query_selector("button:has-text('Вход'), button[type='submit']")
            await submit_btn.click()
            await page.wait_for_timeout(2000)

        screenshot_path2 = r"C:\Users\Salomanov\.gemini\antigravity\brain\69ccc142-f237-439d-bcb7-bba5087ae205\13_port_90_mobile_logged_in.png"
        await page.screenshot(path=screenshot_path2, full_page=True)
        print(f"Mobile logged in screenshot: {screenshot_path2}")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
