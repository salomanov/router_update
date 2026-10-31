import sys
import asyncio
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="msedge")
        # New context = completely empty cookies and storage
        context = await browser.new_context()
        page = await context.new_page()

        errors = []
        page.on("console", lambda msg: errors.append(f"[CONSOLE {msg.type}] {msg.text}") if msg.type in ['error'] else None)
        page.on("pageerror", lambda exc: errors.append(f"[PAGE ERROR] {exc}"))

        def handle_response(response):
            if response.status >= 400:
                errors.append(f"[HTTP {response.status}] {response.request.method} {response.url}")

        page.on("response", handle_response)

        print("Navigating to http://192.168.1.1:90/ in fresh incognito context...")
        await page.goto("http://192.168.1.1:90/", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # Check if login modal is present
        user_input = await page.query_selector("input[type='text'], input:not([type='password'])")
        pass_input = await page.query_selector("input[type='password']")
        print(f"Login modal present? {user_input is not None and pass_input is not None}")

        title = await page.title()
        print(f"Page title: {title}")

        screenshot_path = r"C:\Users\Salomanov\.gemini\antigravity\brain\69ccc142-f237-439d-bcb7-bba5087ae205\14_port_90_anonymous_direct.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot saved: {screenshot_path}")

        print("\nErrors encountered:")
        for err in errors:
            print(err)
        if not errors:
            print("Zero errors! Completely clean!")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
