import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Navigating...")
        await page.goto("https://www.cricway.online")
        await page.wait_for_timeout(5000)
        
        print("Logging in...")
        login_btn = page.locator("button, a, div").filter(has_text="Login | Signup").first
        if await login_btn.count() == 0:
            login_btn = page.locator("button, a, div").filter(has_text="Login").first
            
        if await login_btn.count() > 0:
            await login_btn.click()
            await page.wait_for_timeout(2000)
            
        await page.locator("input[type='text']").first.fill("Shinchanchan")
        pass_inputs = page.locator("input[type='password']")
        if await pass_inputs.count() > 0:
            await pass_inputs.first.fill("Shinchan@2001")
            
        await page.keyboard.press("Enter")
        print("Waiting 10s after login...")
        await page.wait_for_timeout(10000)
        
        await page.screenshot(path="after_login.png")
        print("Screenshot saved.")
        
        deposit_btn = page.locator("a, button, div, span, li, p").filter(has_text="DEPOSIT")
        print(f"Elements with 'DEPOSIT': {await deposit_btn.count()}")
        
        await browser.close()

asyncio.run(main())
