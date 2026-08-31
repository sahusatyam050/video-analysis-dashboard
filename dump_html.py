import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://k777.cool/normal/")
        await page.wait_for_timeout(5000)
        html = await page.content()
        with open("k777_dom.html", "w") as f:
            f.write(html)
        await browser.close()

asyncio.run(main())
