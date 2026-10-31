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
        page.on("pageerror", lambda exc: print(f"[PAGE ERROR] {exc}"))

        def handle_response(response):
            if response.status >= 400:
                print(f"[HTTP {response.status}] {response.url}")

        page.on("response", handle_response)

        print("Navigating to http://192.168.1.1:90/ ...")
        try:
            res = await page.goto("http://192.168.1.1:90/", wait_until="networkidle", timeout=15000)
            print(f"Main response status: {res.status if res else 'None'}")
        except Exception as e:
            print(f"Goto error: {e}")

        await page.wait_for_timeout(3000)

        title = await page.title()
        print(f"Page title: {title}")

        # Take screenshot
        screenshot_path = r"C:\Users\Salomanov\.gemini\antigravity\brain\69ccc142-f237-439d-bcb7-bba5087ae205\10_port_90_view.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot saved to {screenshot_path}")

        # Check visible text
        text = await page.inner_text("body")
        print(f"Body text:\n{text}")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
