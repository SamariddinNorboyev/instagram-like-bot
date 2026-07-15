import asyncio
from playwright.async_api import Page, BrowserContext

async def _handle_instagram_popups(page: Page, context: BrowserContext, cookie_path: str | None = None) -> None:
    """
    Instagram sahifalarida to'satdan chiqadigan barcha pop-up va 
    bildirishnoma oynalarini ("OK", "Save info", va h.k.) birma-bir tozalaydi.
    """
    try:
        ok_button = page.locator(
            "button:has-text('OK'), "
            "button:has-text('Ok'), "
            "[role='button']:has-text('OK'), "
            "[role='button']:has-text('Ok')"
        ).first
        if await ok_button.is_visible(timeout=2500):
            await ok_button.click(force=True)
            await asyncio.sleep(2)

        save_info_button = page.locator(
            "button:has-text('Save info'), "
            "button:has-text('Save Info'), "
            "div[role='button']:has-text('Save info'), "
            "div[role='button']:has-text('Save Info')"
        ).first
        if await save_info_button.is_visible(timeout=2500):
            await save_info_button.click(force=True)
            await asyncio.sleep(3)
            if cookie_path:
                await context.storage_state(path=cookie_path)
                
    except Exception as e:
        print(f"Instagram pop-up oynalarini tozalashda xato yuz berdi: {e}")
