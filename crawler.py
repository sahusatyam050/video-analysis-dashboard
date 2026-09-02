import asyncio
import os
import csv
import logging
import random
import time
import re
from urllib.parse import urlparse
from playwright.async_api import async_playwright, Page, TimeoutError
from playwright_stealth import Stealth

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_seed_credentials(target_url):
    """Parses seed_accounts.csv and returns credentials along with otp requirement."""
    csv_path = os.path.join(os.path.dirname(__file__), "rules", "seed_accounts.csv")
    if not os.path.exists(csv_path):
        return None
    
    target_domain = urlparse(target_url).netloc.replace("www.", "")
    
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            db_domain = urlparse(row.get("Url", "")).netloc.replace("www.", "")
            if target_domain == db_domain or target_domain in db_domain or db_domain in target_domain:
                otp_val = str(row.get("OTP (Y/N)", "")).strip().lower()
                otp_req = otp_val in ["yes", "y", "true"]
                
                # Prioritize Mobile > Email > Username, and completely ignore 'N/A' strings
                def get_valid(val):
                    return val if val and str(val).strip().upper() != "N/A" else None
                    
                username = get_valid(row.get("Mobile Number")) or \
                           get_valid(row.get("E-mail ID")) or \
                           get_valid(row.get("Username"))
                           
                return {
                    "username": username,
                    "password": row.get("Password"),
                    "otp_required": otp_req
                }
    return None

async def close_popups(page: Page):
    """Attempt to find and close promotional popups / modals."""
    try:
        close_selectors = [
            "button:has-text('Close')", "button:has-text('Skip')",
            ".close", ".close-btn", ".modal-close", ".btn-close",
            "[aria-label='Close']", "[aria-label='close']",
            "i.fa-times", "i.fa-close", "svg.close-icon",
            "div:has-text('✕')", "span:has-text('✕')",
            "div:has-text('✖')", "span:has-text('✖')",
            ".absolute.top-4.right-4 button",
            ".absolute > button:has(svg)"
        ]
        for sel in close_selectors:
            loc = page.locator(sel).first
            if await loc.count() > 0 and await loc.is_visible():
                logging.info(f"Found popup close button ({sel}). Clicking...")
                await loc.click(force=True)
                await page.wait_for_timeout(2000)
                break
    except Exception as e:
        logging.info(f"Error while trying to close popups: {e}")

async def phase_1_authentication(page: Page, creds: dict, otp_callback=None, state_callback=None) -> bool:
    """Critical Phase: Attempt to log in using injected credentials."""
    logging.info("Phase 1: Starting Authentication...")
    if state_callback:
        state_callback("current_phase", "auth")
        
    try:
        # Pre-login splash page check
        inputs_count = await page.locator("input").count()
        if inputs_count == 0:
            logging.info("No inputs found on page. Checking for 'Play now' or 'Enter' splash screens...")
            splash_btn = page.locator("a, button, div").filter(has_text=re.compile(r"^(play now|enter|web version|continue)$", re.IGNORECASE)).first
            if await splash_btn.count() > 0 and await splash_btn.is_visible():
                logging.info("Found splash screen button. Clicking to reach main app...")
                await splash_btn.click()
                await page.wait_for_timeout(5000)
                
        await close_popups(page)
                

                
        # Wait for potential login buttons to appear
        login_btn = page.locator("button, a, div").filter(has_text=re.compile(r"(login|sign in|log in)", re.IGNORECASE)).first
        
        try:
            await login_btn.wait_for(state="visible", timeout=10000)
            await login_btn.click()
            await page.wait_for_timeout(2000)
        except TimeoutError:
            logging.info("No explicit login button found, assuming login form is already on screen.")
        
        # Fill credentials
        # Find username/mobile input
        user_selectors = [
            'input[placeholder*="obile" i]',
            'input[placeholder*="hone" i]',
            'input[placeholder*="umber" i]',
            'input[placeholder*="ser" i]',
            'input[placeholder*="ccount" i]',
            'input[type="tel"]',
            'input[type="number"]',
            'input[type="text"]',
            'input[type="email"]',
            'input[name*="mobile" i]',
            'input[name*="phone" i]',
            'input[name*="user" i]',
            'input' # fallback to first input
        ]
        
        user_input = None
        for selector in user_selectors:
            loc = page.locator(selector).first
            if await loc.count() > 0 and await loc.is_visible():
                user_input = loc
                break
                
        if not user_input:
            raise Exception("Could not find any username/mobile input field.")
            
        logging.info("Typing username letter-by-letter to bypass bot detection...")
        await user_input.focus()
        await user_input.press_sequentially(creds["username"], delay=150)
        
        # Find password input
        pass_input = page.locator('input[type="password"]').first
        if await pass_input.count() > 0 and await pass_input.is_visible():
            await pass_input.focus()
            await pass_input.press_sequentially(creds["password"], delay=150)
        else:
            # Fallback to second input
            fallback_input = page.locator('input').nth(1)
            await fallback_input.focus()
            await fallback_input.press_sequentially(creds["password"], delay=150)
        
        # Submit
        submit_btn = page.locator("button, input[type='submit']").filter(has_text=re.compile(r"^(login|sign in|log in|submit|get otp|request otp)$", re.IGNORECASE)).first
        await submit_btn.click()
        
        if creds.get("otp_required") and otp_callback:
            logging.info("Site requires OTP. Pausing crawler and signaling Dashboard...")
            otp_code = await otp_callback()
            if otp_code:
                logging.info(f"Received OTP: {otp_code}. Filling OTP form...")
                otp_input = page.locator('input[type="text"], input[type="number"], input').filter(has_text=re.compile(r"(otp|code|verify)", re.IGNORECASE)).first
                if await otp_input.count() == 0:
                    otp_input = page.locator('input').last # Fallback to last input if specific locator fails
                
                await otp_input.fill(otp_code)
                verify_btn = page.locator("button").filter(has_text=re.compile(r"^(verify|submit|confirm|login)$", re.IGNORECASE)).first
                await verify_btn.click()
        
        # Wait for navigation or successful login indicator (e.g. Deposit button appearing)
        logging.info("Credentials/OTP submitted. Waiting 8s for dashboard to load...")
        await page.wait_for_timeout(8000)
        return True
        
    except Exception as e:
        logging.warning(f"Phase 1 Authentication Failed: {e}")
        return False
        
async def phase_2_context_exploration(page: Page, state_callback=None):
    """Non-Critical Phase: Click around randomly to build trust and capture game lobby."""
    logging.info("Phase 2: Contextual Exploration...")
    if state_callback:
        state_callback("current_phase", "context")
        
    await close_popups(page)
    try:
        # Scroll a bit
        await page.evaluate("window.scrollBy({top: 500, behavior: 'smooth'})")
        await page.wait_for_timeout(2000)
        
        # Look for Casino, Sports, Aviator
        gambling_links = page.locator("a, button").filter(has_text=re.compile(r"(casino|sports|live|aviator|slots)", re.IGNORECASE))
        if await gambling_links.count() > 0:
            target = gambling_links.first
            if await target.is_visible():
                logging.info(f"Found gaming context link. Clicking...")
                await target.click(timeout=3000)
                await page.wait_for_timeout(4000)
        else:
            logging.info("No explicit gaming links found in Phase 2.")
    except Exception as e:
        logging.warning(f"Phase 2 skipped due to timeout/error: {e}")

async def phase_3_affiliate_profile(page: Page, state_callback=None):
    """Non-Critical Phase: Look for Profile/Promotions for MLM evidence."""
    logging.info("Phase 3: Affiliate & Profile Evidence...")
    if state_callback:
        state_callback("current_phase", "affiliate")
        
    await close_popups(page)
    try:
        promo_links = page.locator("a, button").filter(has_text=re.compile(r"(promotion|refer|invite|profile|vip|account)", re.IGNORECASE))
        if await promo_links.count() > 0:
            target = promo_links.first
            if await target.is_visible():
                logging.info("Found Affiliate/Profile link. Clicking...")
                await target.click(timeout=3000)
                await page.wait_for_timeout(5000) # Wait 5s for evidence to render
        else:
            logging.info("No Affiliate/Profile links found in Phase 3.")
    except Exception as e:
        logging.warning(f"Phase 3 skipped due to timeout/error: {e}")

async def phase_4_financial_execution(page: Page, state_callback=None):
    """Critical Phase: Navigate to Deposit and trigger QR Code."""
    logging.info("Phase 4: Financial Execution (Hunting QR Codes)...")
    if state_callback:
        state_callback("current_phase", "financial")
        
    await close_popups(page)
    try:
        deposit_locators = page.locator("a, button, [role='button'], span").filter(has_text=re.compile(r"(deposit|wallet|cashier|recharge|add money)", re.IGNORECASE))
        
        try:
            await deposit_locators.first.wait_for(state="attached", timeout=8000)
        except:
            pass
            
        clicked = False
        count = await deposit_locators.count()
        for i in range(count):
            loc = deposit_locators.nth(i)
            if await loc.is_visible():
                logging.info("Found visible Deposit/Wallet element! Clicking...")
                await loc.scroll_into_view_if_needed()
                await loc.click(force=True)
                clicked = True
                break
                
        if not clicked:
            raise TimeoutError("Could not find a visible deposit button.")
            
        await page.wait_for_timeout(6000)
        # Look for Payment Gateways/Tabs
        payment_tabs = page.locator("a, button, div, span, li").filter(has_text=re.compile(r"^(upi|phonepe|paytm|gpay|google pay|bank|crypto|whatsapp deposit)$", re.IGNORECASE))
        
        count = await payment_tabs.count()
        if count > 0:
            logging.info(f"Found {count} payment option tabs. Exploring up to 3...")
            for i in range(min(count, 3)):
                tab = payment_tabs.nth(i)
                if await tab.is_visible():
                    tab_text = await tab.inner_text()
                    logging.info(f"Clicking payment tab: {tab_text.strip()}")
                    await tab.click(force=True)
                    await page.wait_for_timeout(2000)
                    
                    # Look for amount input
                    amount_input = page.locator("input[placeholder*='amount' i], input[type='number'], input[name*='amount' i]").first
                    if await amount_input.count() > 0 and await amount_input.is_visible():
                        logging.info("Found amount input. Injecting '5000'...")
                        await amount_input.fill("5000")
                        await page.wait_for_timeout(1000)
                        
                        # Sometimes a "Next" button needs to be clicked
                        next_btn = page.locator("button, a").filter(has_text=re.compile(r"^(next|submit|recharge)$", re.IGNORECASE)).first
                        if await next_btn.count() > 0 and await next_btn.is_visible():
                            await next_btn.click(force=True)
                    
                    # Wait for details to populate for video recording
                    logging.info("Waiting for payment details / QR code to render...")
                    await page.wait_for_timeout(4000)
        else:
            # Fallback: Just look for an amount input or QR code directly
            logging.info("No explicit payment tabs found. Checking for amount input...")
            amount_input = page.locator("input[placeholder*='amount' i], input[type='number'], input[name*='amount' i]").first
            if await amount_input.count() > 0 and await amount_input.is_visible():
                logging.info("Found amount input. Injecting '5000'...")
                await amount_input.fill("5000")
                await page.wait_for_timeout(1000)
                
                next_btn = page.locator("button, a").filter(has_text=re.compile(r"^(next|submit|recharge)$", re.IGNORECASE)).first
                if await next_btn.count() > 0 and await next_btn.is_visible():
                    await next_btn.click(force=True)
                
            logging.info("Waiting 8s for Payment page/QR code to render...")
            await page.wait_for_timeout(8000)
        
    except Exception as e:
        logging.warning(f"Phase 4 Failed or Deposit button not found: {e}")


async def crawl_and_record(url: str, duration: int = 60, output_dir: str = "temp_videos", task_id: int = None, otp_callback=None, state_callback=None) -> str:
    """
    Executes the 4-Phase Event-Driven Forensic Crawl.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    if state_callback:
        state_callback("current_phase", "init")

    start_time = time.time()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            record_video_dir=output_dir,
            record_video_size={"width": 1920, "height": 1080},
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        logging.info(f"Navigating to {url}...")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(4000)
        except Exception as e:
            logging.error(f"Navigation failed: {e}")

        # Check for seed credentials
        creds = get_seed_credentials(url)
        
        if creds:
            logging.info(f"Found Seed Credentials for {url}. Username: {creds['username']}, OTP Required: {creds['otp_required']}")
            auth_success = await phase_1_authentication(page, creds, otp_callback, state_callback)
            if not auth_success:
                logging.warning("Auth failed or timed out. Proceeding anyway.")
        else:
            logging.warning("No credentials found for this domain. Proceeding unauthenticated.")
            
        # --- PHASE 2: Context ---
        await phase_2_context_exploration(page, state_callback)
        
        # --- PHASE 3: Affiliate / Profile ---
        await phase_3_affiliate_profile(page, state_callback)
        
        # --- PHASE 4: Financial Gateway ---
        await phase_4_financial_execution(page, state_callback)
        
        # Wait a fixed 5 seconds to ensure final evidence (like QR codes) fully renders
        if state_callback:
            state_callback("current_phase", "finalizing")
            
        logging.info("Crawler finished all phases. Waiting 5s for final page render before stopping recording...")
        for i in range(5):
            if state_callback:
                state_callback("progress", i / 5.0)
            await page.wait_for_timeout(1000)
        
        if state_callback:
            state_callback("progress", 1.0)

        # Final flush
        await page.close()
        video_path = await page.video.path()
        await context.close()
        await browser.close()
        
        logging.info(f"Crawl complete. Video saved to {video_path}")
        return video_path

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
        asyncio.run(crawl_and_record(test_url, duration=60))
