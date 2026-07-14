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
            
            # Kuki tugmasini qidirib bosish
            try:
                cookie_button = page.locator("button:has-text('Allow all cookies'), button:has-text('Allow essential and optional cookies')")
                await cookie_button.wait_for(state="visible", timeout=7000)
                await cookie_button.click()
                # Oyna yopilib ketishi uchun barqaror vaqt kutamiz
                await asyncio.sleep(1.5)
            except Exception:
                pass

            # 1. Inputlar tayyor bo'lishini kutamiz va to'ldiramiz
            await page.wait_for_selector("input[name='username']", state="visible", timeout=15000)
            await page.fill("input[name='username']", username)
            await page.fill("input[name='password']", password)
            
            # 2. LOGIN TUGMASINI ANIQLASH (Kombinatsiyalangan ishonchli locatorlar)
            # Instagram bir nechta variantdan birini ishlatsa ham adashmaydigan selector yaratdik:
            login_button = page.locator(
                "button[type='submit'], "
                "form button, "
                "button._acan._acap._acas._aj1-, " # Instagramning mobil klassi
                "div[role='button']:has-text('Log in'), "
                "button:has-text('Log in')"
            ).first
                        
            # 3. Tugma ekranda to'liq yuklanishini kutamiz va bosamiz
            await login_button.wait_for(state="visible", timeout=10000)
                        
            # Ba'zan virtual kliklar ishlamay qolsa, "force=True" yordam beradi
            await login_button.click(force=True)
        
            # Kirish jarayoni uchun kutish
            error_message_locator = page.locator("[id='alerts'], [class*='_ab8w'] p, [role='alert']")
            # 1. Haqiqatdan ham ekranda xato yozuv chiqdimi?
            if await error_message_locator.is_visible():
                # 2. Chiqqan bo'lsa, o'sha yozuvni (matnni) o'qib olamiz
                alert_text = await error_message_locator.text_content()
                return False, f"Instagram xabari: {alert_text}"
                
                        
            if "login" in page.url:
                # Agar ekranda biror xato matni ko'rinib turgan bo'lsa, o'shani olamiz
                if await error_message_locator.is_visible():
                    alert_text = await error_message_locator.text_content()
                    await browser.close()
                    return False, f"Instagram xabari: {alert_text}"
                
                try:
                    await page.screenshot(path="login_error.png", full_page=True)
                except Exception as screenshot_err:
                    print(f"Screenshot olishda xatolik: {screenshot_err}")         
                # Agar matn yo'q, lekin baribir login sahifasida bo'lsak
                await browser.close()
                return False, "Tizimga kirish rad etildi (Instagram bot deb gumon qilgan bo'lishi mumkin)."
                            
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
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(3)
            
            # Avval layk bosilgan yoki bosilmaganini aniqlaymiz
            already_liked = await page.locator("svg[aria-label='Unlike'], svg[aria-label='Yoqtirishdan voz kechish']").count()
            
            if already_liked > 0:
                await page.screenshot(path=screenshot_path)
                return True, "Ushbu postga avvaldan layk bosilgan!"
            
            like_button = page.locator("span[class*='xp7jhwk'] svg[aria-label='Like'], svg[aria-label='Yurakcha']")
            await like_button.first.click(timeout=7000)
            await asyncio.sleep(1.5)
                
            await page.screenshot(path=screenshot_path)
            return True, ""
            
        except Exception as e:
            try:
                await page.screenshot(path="like_error.png")
            except Exception:
                pass
            return False, str(e)
            
        finally:
            await browser.close()