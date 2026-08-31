import asyncio
import os
import random
from playwright.async_api import async_playwright, Page
from playwright_stealth import Stealth

async def scroll_page(page: Page, duration_seconds: int = 10, scroll_interval: float = 2.0):
    """Scrolls down smoothly."""
    iterations = int(duration_seconds / scroll_interval)
    for _ in range(iterations):
        try:
            await page.evaluate("window.scrollBy({top: 800, behavior: 'smooth'})")
        except Exception:
            pass
        await asyncio.sleep(scroll_interval)

async def click_random_gambling_link(page: Page):
    """Finds an interactive element related to gambling/sports and clicks it."""
    keywords = ["live", "sports", "casino", "slots", "bet", "in-play", "deposit", "register", "login", "games"]
    random.shuffle(keywords) # Randomize priority
    
    try:
        for keyword in keywords:
            # Find links or buttons containing the keyword (case-insensitive)
            locators = page.locator(f"a:has-text('{keyword}'), button:has-text('{keyword}')")
            count = await locators.count()
            
            if count > 0:
                # Pick a random matching element
                idx = random.randint(0, count - 1)
                target = locators.nth(idx)
                if await target.is_visible():
                    print(f"Crawler found interactive element for '{keyword}', clicking...")
                    await target.click(timeout=3000)
                    # Wait for SPA routing or network requests to settle
                    await page.wait_for_timeout(3000)
                    return True
    except Exception as e:
        print(f"Wanderer click error: {e}")
    
    return False

async def crawl_and_record(url: str, duration: int = 40, output_dir: str = "temp_videos") -> str:
    """
    Crawls a URL using stealth mode, explores the page intelligently (Wanderer algorithm),
    and returns the path to the recorded .webm video.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    async with async_playwright() as p:
        # Launch Chromium headless
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"] # Extra stealth
        )
        
        # Configure video recording directory, user-agent, and high-res viewport
        context = await browser.new_context(
            record_video_dir=output_dir,
            record_video_size={"width": 1920, "height": 1080},
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        
        # Apply Playwright Stealth to bypass Cloudflare/anti-bots
        await Stealth().apply_stealth_async(page)
        
        try:
            print(f"Navigating to {url}...")
            # Go to the URL
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            # Give it a couple seconds to load fully or resolve initial Cloudflare challenges
            await page.wait_for_timeout(4000) 
        except Exception as e:
            print(f"Crawler navigation error or timeout: {e}")
            pass

        # The "Wanderer" Algorithm
        # Phase 1: Scroll the homepage
        print("Phase 1: Scrolling homepage...")
        await scroll_page(page, duration_seconds=10)
        
        if duration > 10:
            # Phase 2: Look for an interactive category (Casino, Sports, etc) and click
            print("Phase 2: Looking for deeper links...")
            clicked = await click_random_gambling_link(page)
            
            # Phase 3: Scroll the new page/modal
            remaining_time = duration - 13 # 10s scroll + 3s click wait
            if remaining_time > 0:
                print(f"Phase 3: Scrolling new view for {remaining_time}s...")
                await scroll_page(page, duration_seconds=remaining_time)
            
        # Close the page and context to flush the video to disk
        await page.close()
        video_path = await page.video.path()
        await context.close()
        await browser.close()
        
        return video_path

if __name__ == "__main__":
    # Quick test runner
    import sys
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
        print(f"Intelligent Crawling {test_url}...")
        video = asyncio.run(crawl_and_record(test_url, duration=25))
        print(f"Video saved to: {video}")
