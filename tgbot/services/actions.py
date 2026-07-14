import os
import asyncio
from tgbot.config import COOKIES_DIR
from .popups import _handle_instagram_popups
from playwright.async_api import async_playwright

MODERN_USER_AGENT = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"

async def like_post_and_screenshot(user_id: int, post_url: str, screenshot_path: str) -> tuple[bool, str]:
    cookie_path = f"{COOKIES_DIR}/{user_id}.json"
    
    if not os.path.exists(cookie_path):
        return False, "Avval ro'yxatdan o'ting (tizimga kiring)!"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=cookie_path,
            viewport={"width": 375, "height": 812},
            user_agent=MODERN_USER_AGENT
        )
        page = await context.new_page()
        
        try:
            await page.goto(post_url)
            try:
                await page.wait_for_load_state("networkidle", timeout=4.0)
            except Exception:
                pass
            
            # Tizimda bormizni yoki yo'qligimizni tekshiramiz
            is_logged_in = await page.locator("a[href*='/accounts/login/'], button:has-text('Log in'), button:has-text('log in')").count() == 0
                        
            if not is_logged_in:
                await browser.close()
                return False, "Sessiya muddati tugagan (Kukilar eskirgan). Iltimos, profilingizga qaytadan kiring: /start"
                
            # Pop-up va bildirishnomalarni shu yerda ham tekshirib tozalaymiz
            await _handle_instagram_popups(page, context, cookie_path)

            # 3. "Continue on web" tugmasi chiqsa bosamiz
            try:
                continue_web = page.locator("a:has-text('Continue on web'), button:has-text('Continue on web'), [role='button']:has-text('Continue on web')").first
                if await continue_web.is_visible():
                    await continue_web.click()
                    await asyncio.sleep(3)
            except Exception:
                pass

            # 4. Agar boshqa turdagi kichik yopish ("X") tugmalari bo'lsa
            try:
                close_button = page.locator("svg[aria-label='Close'], svg[aria-label='Yopish']").first
                if await close_button.is_visible():
                    await close_button.click()
                    await asyncio.sleep(1)
            except Exception:
                pass

            # 5. Layk bosilgan/bosilmaganini tekshirish
            already_liked_locator = page.locator(
                "svg[aria-label='Unlike'], "
                "svg[aria-label='Yoqtirishdan voz kechish'], "
                "span svg[fill='rgb(255, 48, 64)']" # Qizil yurakcha rangi bo'yicha
            ).first
            
            if await already_liked_locator.is_visible(timeout=3000):
                await page.screenshot(path=screenshot_path)
                return True, "Ushbu postga avvaldan layk bosilgan!"
                        
            # 6. Agar layk bosilmagan bo'lsa, bosish qismini ishga tushiramiz
            like_button = page.locator(
                "span[class*='xp7jhwk'] svg[aria-label='Like'], "
                "svg[aria-label='Like'], "
                "svg[aria-label='Yoqtirish'], "
                "svg[aria-label='Yurakcha'], "
                "button:has(svg[aria-label='Like'])"
            ).first
                        
            # Tugma ko'rinishini kutamiz va bosamiz
            await like_button.wait_for(state="visible", timeout=5000)
            await like_button.click(force=True)
            await asyncio.sleep(3) # Layk serverga yetib borishini kutamiz
                            
            await page.screenshot(path=screenshot_path)
            return True, ""
            
        except Exception as e:
            try:
                await page.screenshot(path=f"like_error_{user_id}.png")
            except Exception:
                pass
            return False, str(e)
            
        finally:
            await browser.close()