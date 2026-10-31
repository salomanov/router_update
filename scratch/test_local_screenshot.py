import sys
import asyncio
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="msedge")
        page = await browser.new_page()

        print("Navigating to http://192.168.1.1:8089/ ...")
        await page.goto("http://192.168.1.1:8089/", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        path = r"C:\Users\Salomanov\.gemini\antigravity\brain\69ccc142-f237-439d-bcb7-bba5087ae205\17_local_8089_verified.png"
        await page.screenshot(path=path, full_page=True)
        print(f"Screenshot saved to {path}")

        body = await page.inner_text("body")
        print(f"Body text preview:\n{body[:400]}")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
