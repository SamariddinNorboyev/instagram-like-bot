import asyncio
import os
import re
from aiogram.types import AcceptedGiftTypes
from playwright.async_api import async_playwright
from tgbot.config import COOKIES_DIR
from .popups import _handle_instagram_popups

MODERN_USER_AGENT = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
ACTIVE_2FA_SESSIONS = {}


async def login_and_save_session(user_id: int, username: str, password: str) -> tuple[bool, str]:
    if not os.path.exists(COOKIES_DIR):
        os.makedirs(COOKIES_DIR, exist_ok=True)

    cookie_path = f"{COOKIES_DIR}/{user_id}.json"

    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(
        viewport={"width": 375, "height": 812},
        user_agent=MODERN_USER_AGENT,
    )
    page = await context.new_page()
    
    try:
        await page.goto("https://www.instagram.com/accounts/login/")
    
        try:
            cookie_button = page.locator("button:has-text('Allow all cookies'), button:has-text('Allow essential and optional cookies')")
            await cookie_button.wait_for(state="visible", timeout=5000)
            await cookie_button.click()
        except Exception:
            pass
    
        await page.wait_for_selector("input[name='username']", state="visible", timeout=15000)
        await page.fill("input[name='username']", username)
        await page.fill("input[name='password']", password)
    
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
    
        try:
            await page.locator("input[placeholder*='ode'], input[name='verificationCode'], input#code").first.wait_for(state="visible", timeout=15000)
        except Exception:
            pass

        page_text = await page.evaluate("document.body.innerText")
        is_2fa = "Check your" in page_text or "Confirm it's you" in page_text or "Code" in page_text

        if is_2fa:
            ACTIVE_2FA_SESSIONS[user_id] = {
                "playwright": p,
                "browser": browser,
                "context": context,
                "page": page,
                "cookie_path": cookie_path
            }
            return False, "2fa_required"
            
        try:
            await page.wait_for_url(lambda url: "login" not in str(url), timeout=7000)
        except Exception:
            pass
    
        if "login" in page.url:
            error_message_locator = page.locator("[id='alerts'], [class*='_ab8w'] p, [role='alert']")
            if await error_message_locator.is_visible():
                alert_text = await error_message_locator.text_content()
                await browser.close()
                await p.stop()
                return False, f"Instagram xabari: {alert_text}"
    
            await browser.close()
            await p.stop()
            return False, "Login yoki parol noto'g'ri."
    
        try:
            await _handle_instagram_popups(page, context)
            await asyncio.sleep(1)
        except Exception as popup_err:
            print(f"Pop-up tozalashda kichik xatolik (o'tkazib yuborildi): {popup_err}")
    
        try:
            await context.storage_state(path=cookie_path)
            await asyncio.sleep(0.5)
        except Exception as cookie_err:
            await browser.close()
            await p.stop()
            return False, f"Sessiyani saqlashda xatolik yuz berdi: {cookie_err}"
        await browser.close()
        await p.stop()
        return True, ""
    
    except Exception as e:
        try:
            await page.screenshot(path=f"login_error_{user_id}.png", full_page=True)
        except Exception as screenshot_err:
            print(f"Screenshot olishda xatolik: {screenshot_err}")
    
        await browser.close()
        await p.stop()
        return False, str(e)    


async def submit_2fa_code_and_save(user_id: int, code: str) -> tuple[bool, str]:
    """Saqlab turilgan brauzer sessiyasiga 2FA kodini kiritadi va sessiyani saqlaydi."""
    session_data = ACTIVE_2FA_SESSIONS.get(user_id)
    if not session_data:
        return False, "Faol login sessiyasi topilmadi. Iltimos, qaytadan urinib ko'ring."

    p = session_data["playwright"]
    browser = session_data["browser"]
    context = session_data["context"]
    page = session_data["page"]
    cookie_path = session_data["cookie_path"]

    try:
        await page.locator("input").first.wait_for(state="visible", timeout=10000)
        await page.locator("input").first.fill(code)

        submit_btn = page.locator(
            "button[type='button']:has-text('Confirm'), "
            "button:has-text('Confirm'), "
            "button:has-text('Continue'), "
            "div[role='button']:has-text('Confirm'), "
            "div[role='button']:has-text('Continue'), "
            "button[type='submit'], "
            "[aria-label='Confirm']"
        ).first
        
        await submit_btn.wait_for(state="visible", timeout=10000)
        await submit_btn.click(force=True)

        try:
            await page.wait_for_selector("svg[aria-label='Home'], svg[aria-label='Direct']", timeout=10000)
        except Exception:
                pass

        if "login" in page.url or await page.locator("input[name='Code']").is_visible():
            await page.screenshot(path=f"login_error_{user_id}.png", full_page=True)
            await browser.close()
            await p.stop()
            ACTIVE_2FA_SESSIONS.pop(user_id, None)
            return False, "Kiritilgan 2FA kod noto'g'ri yoki uning muddati o'tgan."

        try:
            await _handle_instagram_popups(page, context)
            await asyncio.sleep(1)
        except Exception:
            pass

        try:
            await context.storage_state(path=cookie_path)
            await asyncio.sleep(0.5)
        except Exception as cookie_err:
            await browser.close()
            await p.stop()
            ACTIVE_2FA_SESSIONS.pop(user_id, None)
            return False, f"Sessiyani saqlashda xatolik: {cookie_err}"

        await browser.close()
        await p.stop()
        ACTIVE_2FA_SESSIONS.pop(user_id, None)
        return True, ""

    except Exception as e:
        await browser.close()
        await p.stop()
        ACTIVE_2FA_SESSIONS.pop(user_id, None)
        return False, f"Kutilmagan xatolik yuz berdi: {str(e)}"