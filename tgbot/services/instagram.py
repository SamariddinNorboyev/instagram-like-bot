# PlayWritght browser skriptlari
import os
import asyncio
from playwright.async_api import async_playwright
from tgbot.config import COOKIES_DIR

async def login_and_save_session(user_id: int, username: str, password: str) -> tuple[bool, str]:
    cookie_path = f"{COOKIES_DIR}/{user_id}.json"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 375, "height": 812},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1"
        )
        page = await context.new_page()
        
        try:
            await page.goto("https://www.instagram.com/accounts/login/")
            await page.wait_for_selector("input[name='username']", timeout=15000)
            
            await page.fill("input[name='username']", username)
            await page.fill("input[name='password']", password)
            await page.click("button[type='submit']")
            
            await asyncio.sleep(5)
            
            if "login" in page.url:
                await browser.close()
                return False, "Login yoki parol noto'g'ri."
                
            await context.storage_state(path=cookie_path)
            await browser.close()
            return True, ""
            
        except Exception as e:
            await browser.close()
            return False, str(e)


async def like_post_and_screenshot(user_id: int, post_url: str, screenshot_path: str) -> tuple[bool, str]:
    cookie_path = f"{COOKIES_DIR}/{user_id}.json"
    
    if not os.path.exists(cookie_path):
        return False, "Avval ro'yxatdan o'ting!"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=cookie_path,
            viewport={"width": 375, "height": 812},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1"
        )
        page = await context.new_page()
        
        try:
            await page.goto(post_url)
            await asyncio.sleep(3)
            
            like_button_selector = "span[class*='xp7jhwk'] svg[aria-label='Like'], svg[aria-label='Yurakcha']"
            try:
                await page.click(like_button_selector, timeout=5000)
                await asyncio.sleep(1)
            except Exception:
                pass
                
            await page.screenshot(path=screenshot_path)
            await browser.close()
            return True, ""
            
        except Exception as e:
            await browser.close()
            return False, str(e)