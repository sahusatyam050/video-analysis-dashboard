import asyncio
import os
from playwright.async_api import async_playwright

async def crawl_and_record(url: str, duration: int = 40, output_dir: str = "temp_videos") -> str:
    """
    Crawls a URL blindly, scrolls down for the specified duration,
    and returns the path to the recorded .webm video.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    async with async_playwright() as p:
        # Launch Chromium headless
        browser = await p.chromium.launch(headless=True)
        
        # Configure video recording directory and high-res viewport
        context = await browser.new_context(
            record_video_dir=output_dir,
            record_video_size={"width": 1920, "height": 1080},
            viewport={"width": 1920, "height": 1080}
        )
        
        page = await context.new_page()
        
        try:
            # Navigate to the URL
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            # Give it a couple seconds to load fully
            await page.wait_for_timeout(2000) 
        except Exception as e:
            print(f"Crawler navigation error or timeout: {e}")
            # Continue even if it times out, to capture whatever loaded
            pass

        # Blind scrolling logic
        # Scroll down smoothly every 2 seconds
        scroll_interval = 2.0
        iterations = int(duration / scroll_interval)
        
        for _ in range(iterations):
            # Evaluate JS to scroll down
            await page.evaluate("window.scrollBy({top: 800, behavior: 'smooth'})")
            await asyncio.sleep(scroll_interval)
            
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
        print(f"Crawling {test_url}...")
        video = asyncio.run(crawl_and_record(test_url, duration=15))
        print(f"Video saved to: {video}")
