# tgbot/services/instagram.py
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
            try:
                cookie_button = page.locator("button:has-text('Allow all cookies'), button:has-text('Allow essential and optional cookies')")
                await cookie_button.wait_for(state="visible", timeout=7000)
                await cookie_button.click()
                await asyncio.sleep(1)
            except Exception:
                pass

            await page.wait_for_selector("input[name='username']", timeout=15000)
            await page.fill("input[name='username']", username)
            await page.fill("input[name='password']", password)
            login_button = page.locator("button[type='submit'], button:has-text('Log in')").first
            await login_button.wait_for(state="visible", timeout=10000)
            await login_button.click()
        
            await asyncio.sleep(5)
            
            # Login muvaffaqiyatli o'tganini tekshirish
            if "login" in page.url:
                await browser.close()
                return False, "Login yoki parol noto'g'ri."
                
            await context.storage_state(path=cookie_path)
            await browser.close()
            return True, ""
            
        except Exception as e:
            try:
                await page.screenshot(path="login_error.png", full_page=True)
            except Exception as screenshot_err:
                print(f"Screenshot olishda xatolik: {screenshot_err}")
                        
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
            await page.wait_for_load_state("networkidle") # Sahifa to'liq yuklanishini kutamiz
            await asyncio.sleep(3)
            
            # "Unlike" tugmasi bor-yo'qligini tekshiramiz (agar avvalroq layk bosilgan bo'lsa)
            already_liked = await page.locator("svg[aria-label='Unlike'], svg[aria-label='Yoqtirishdan voz kechish']").count()
            
            if already_liked > 0:
                # Avvaldan layk bosilgan bo'lsa, qayta bosmaymiz
                await page.screenshot(path=screenshot_path)
                return True, "Ushbu postga avvaldan layk bosilgan!"
            
            # Agar layk bosilmagan bo'lsa, bosamiz
            like_button = page.locator("span[class*='xp7jhwk'] svg[aria-label='Like'], svg[aria-label='Yurakcha']")
            await like_button.first.click(timeout=7000)
            await asyncio.sleep(1.5) # Layk animatsiyasi tugashini kutamiz
                
            await page.screenshot(path=screenshot_path)
            return True, ""
            
        except Exception as e:
            # Xatolik bo'lsa ham tushunarsiz vaziyatni rasmga olamiz
            try:
                await page.screenshot(path="like_error.png")
            except Exception:
                pass
            return False, str(e)
            
        finally:
            # Brauzer har qanday holatda ham (xato chiqsa ham) xotirada qolib ketmasligi uchun yopiladi
            await browser.close()