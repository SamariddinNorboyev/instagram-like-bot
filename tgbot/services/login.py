import os
import asyncio
from tgbot.config import COOKIES_DIR
from .popups import _handle_instagram_popups
from playwright.async_api import async_playwright

MODERN_USER_AGENT = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"

async def login_and_save_session(user_id: int, username: str, password: str) -> tuple[bool, str]:
    # Kuki saqlanadigan papka mavjudligini tekshiramiz
    if not os.path.exists(COOKIES_DIR):
        os.makedirs(COOKIES_DIR, exist_ok=True)
        
    cookie_path = f"{COOKIES_DIR}/{user_id}.json"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 375, "height": 812},
            user_agent=MODERN_USER_AGENT
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
                "div[role='button']:has-text('Log in'), "
                "div[role='button']:has-text('log in'), "
                "button:has-text('Log in'), "
                "button:has-text('log in'), "
                "[aria-label='Log in'], "
                "form button"
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

            # Pop-up va bildirishnomalarni tozalash (Save info bilan birga)
            await _handle_instagram_popups(page, context)

            await asyncio.sleep(3)
            
            # MUHIM: Sessiya (Kuki)ni to'liq saqlaymiz
            await context.storage_state(path=cookie_path)
            await asyncio.sleep(2)  # Fayl tizimiga yozilishini kutamiz
            await browser.close()
            return True, ""
            
        except Exception as e:
            try:
                await page.screenshot(path=f"login_error_{user_id}.png", full_page=True)
            except Exception as screenshot_err:
                print(f"Screenshot olishda xatolik: {screenshot_err}")
                        
            await browser.close()
            return False, str(e)