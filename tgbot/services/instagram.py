import os
import asyncio
from playwright.async_api import async_playwright, Page, BrowserContext
from tgbot.config import COOKIES_DIR


# Instagram to'liq qo'llab-quvvatlaydigan eng yengil mobil Chrome User-Agent
MODERN_USER_AGENT = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"


async def _handle_instagram_popups(page: Page, context: BrowserContext, cookie_path: str = None) -> None:
    """
    Instagram sahifalarida to'satdan chiqadigan barcha pop-up va 
    bildirishnoma oynalarini ("OK", "Save info", va h.k.) birma-bir tozalaydi.
    """
    try:
        # 1. "The messaging tab has a new look" kabi xabarlarning "OK" tugmasi
        ok_button = page.locator(
            "button:has-text('OK'), "
            "button:has-text('Ok'), "
            "[role='button']:has-text('OK'), "
            "[role='button']:has-text('Ok')"
        ).first
        if await ok_button.is_visible(timeout=2500):
            await ok_button.click(force=True)
            await asyncio.sleep(2)

        # 2. "Save login info" oynasidagi "Save info" tugmasi
        save_info_button = page.locator(
            "button:has-text('Save info'), "
            "button:has-text('Save Info'), "
            "div[role='button']:has-text('Save info'), "
            "div[role='button']:has-text('Save Info')"
        ).first
        if await save_info_button.is_visible(timeout=2500):
            await save_info_button.click(force=True)
            await asyncio.sleep(3)
            # Agar kuki yo'li berilgan bo'lsa, yangi holatni faylga yozamiz
            if cookie_path:
                await context.storage_state(path=cookie_path)
                
    except Exception as e:
        print(f"Instagram pop-up oynalarini tozalashda xato yuz berdi: {e}")


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
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(4)
            
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