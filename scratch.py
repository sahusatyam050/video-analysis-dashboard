import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.cricway.online/exchange_sports/inplay")
        await page.wait_for_timeout(5000)
        
        # Log all class names containing modal or close or popup
        html = await page.content()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        for el in soup.find_all(class_=lambda c: c and any(kw in c.lower() for kw in ['modal', 'close', 'popup', 'dialog', 'overlay'])):
            print(f"<{el.name} class='{' '.join(el.get('class'))}'> text: {el.text.strip()[:30]}")
            
        await browser.close()

asyncio.run(main())
