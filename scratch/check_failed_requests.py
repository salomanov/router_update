import sys
import asyncio
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="msedge")
        page = await browser.new_page()

        page.on("requestfailed", lambda req: print(f"REQUEST FAILED: {req.method} {req.url} -> {req.failure}"))

        await page.goto("http://192.168.1.1:90/", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
