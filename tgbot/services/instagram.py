# tgbot/services/instagram.py
import os
import asyncio
from playwright.async_api import async_playwright
from tgbot.config import COOKIES_DIR

async def login_and_save_session(user_id: int, username: str, password: str) -> tuple[bool, str]:
    # Kuki saqlanadigan papka mavjudligini tekshiramiz
    if not os.path.exists(COOKIES_DIR):
        os.makedirs(COOKIES_DIR, exist_ok=True)
        
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
            
            # Kuki oynasini qabul qilish
            try:
                cookie_button = page.locator("button:has-text('Allow all cookies'), button:has-text('Allow essential and optional cookies')")
                await cookie_button.wait_for(state="visible", timeout=5000)
                await cookie_button.click()
                await asyncio.sleep(1.5)
            except Exception:
                pass

            # Login va parolni kiritish
            await page.wait_for_selector("input[name='username']", state="visible", timeout=15000)
            await page.fill("input[name='username']", username)
            await page.fill("input[name='password']", password)

            # Login tugmasini bosish
            login_button = page.locator(
                "button[type='submit'], "
                "form button, "
                "button._acan._acap._acas._aj1-, "
                "button:has-text('Log in')"
            ).first
            
            await login_button.wait_for(state="visible", timeout=10000)
            await login_button.click(force=True)
            
            # Login amalga oshishini va sahifa yangilanishini kutamiz
            await asyncio.sleep(8)
            
            # Agar URL manzilida hali ham login so'zi bo'lsa, xatolikni aniqlaymiz
            if "login" in page.url:
                error_message_locator = page.locator("[id='alerts'], [class*='_ab8w'] p, [role='alert']")
                if await error_message_locator.is_visible():
                    alert_text = await error_message_locator.text_content()
                    await browser.close()
                    return False, f"Instagram xabari: {alert_text}"
                
                await browser.close()
                return False, "Login yoki parol noto'g'ri."

            await page.wait_for_url("**/instagram.com/**", timeout=15000)
            await asyncio.sleep(5)
            
            # MUHIM: Sessiya (Kuki)ni to'liq saqlaymiz
            await context.storage_state(path=cookie_path)
            await asyncio.sleep(2) # Fayl tizimiga yozilishini kutamiz
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
        return False, "Avval ro'yxatdan o'ting (tizimga kiring)!"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=cookie_path,
            viewport={"width": 375, "height": 812},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1"
        )
        page = await context.new_page()
        
        try:
            # 1. Post sahifasiga o'tamiz va yuklanishini kutamiz
            await page.goto(post_url)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(4)
            
            # 2. SHU YERGA QO'SHILDI: Tizimga kirganimizni tekshiramiz
            is_logged_in = await page.locator("a[href*='/accounts/login/'], button:has-text('Log in'), button:has-text('log in')").count() == 0
            if not is_logged_in:
                await browser.close()
                return False, "Sessiya muddati tugagan. Iltimos, qaytadan login qiling (/start)!"

            # 3. Agar "Continue on web" tugmasi chiqsa, bosamiz
            try:
                continue_web = page.locator("a:has-text('Continue on web'), button:has-text('Continue on web'), [role='button']:has-text('Continue on web')").first
                if await continue_web.is_visible():
                    await continue_web.click()
                    await asyncio.sleep(3)
            except Exception:
                pass

            # 4. Agar har xil qalqib chiquvchi (pop-up) oynalar bo'lsa, yopamiz
            try:
                close_button = page.locator("svg[aria-label='Close'], svg[aria-label='Yopish']").first
                if await close_button.is_visible():
                    await close_button.click()
                    await asyncio.sleep(1)
            except Exception:
                pass

            # 5. Layk bosilgan/bosilmaganini tekshirish
            already_liked = await page.locator("svg[aria-label='Unlike'], svg[aria-label='Yoqtirishdan voz kechish']").count()
            if already_liked > 0:
                await page.screenshot(path=screenshot_path)
                return True, "Ushbu postga avvaldan layk bosilgan!"
            
            # 6. Layk tugmasini bosish
            like_button = page.locator(
                "span[class*='xp7jhwk'] svg[aria-label='Like'], "
                "svg[aria-label='Like'], "
                "svg[aria-label='Yurakcha'], "
                "button:has(svg[aria-label='Like'])"
            ).first
            
            await like_button.wait_for(state="visible", timeout=10000)
            await like_button.click(force=True)
            await asyncio.sleep(2)
                
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