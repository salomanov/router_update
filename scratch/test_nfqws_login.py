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
            print(f"[HTTP {response.status}] {response.request.method} {response.url}")

        page.on("response", handle_response)

        print("Navigating to http://192.168.1.1:90/ ...")
        await page.goto("http://192.168.1.1:90/", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Fill login form
        # Let's find inputs
        inputs = await page.query_selector_all("input")
        print(f"Found {len(inputs)} inputs")

        # Let's test root / keenetic
        print("Trying username: root, password: keenetic")
        # Find username and password inputs
        user_input = await page.query_selector("input[type='text'], input:not([type='password'])")
        pass_input = await page.query_selector("input[type='password']")

        if user_input and pass_input:
            await user_input.fill("root")
            await pass_input.fill("keenetic")
            
            # Click submit button
            submit_btn = await page.query_selector("button:has-text('Вход'), button[type='submit']")
            if submit_btn:
                print("Clicking submit button...")
                await submit_btn.click()
                await page.wait_for_timeout(3000)
            else:
                print("Submit button not found!")
        else:
            print("Inputs not found!")

        # Take screenshot
        screenshot_path = r"C:\Users\Salomanov\.gemini\antigravity\brain\69ccc142-f237-439d-bcb7-bba5087ae205\11_port_90_after_login.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot saved to {screenshot_path}")

        body_text = await page.inner_text("body")
        print(f"Body text after login:\n{body_text[:500]}")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
