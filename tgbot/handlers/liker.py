# tgbot/handlers/liker.py
import os
import re
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove, FSInputFile, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from tgbot.states.bot_states import BotState
from tgbot.services.instagram import login_and_save_session, like_post_and_screenshot

liker_router = Router()

@liker_router.message(BotState.waiting_for_agreement, F.text.lower() == "ha")
async def agreement_yes(message: Message, state: FSMContext) -> None:
    await state.set_state(BotState.waiting_for_credentials)
    await message.answer(
        "Instagram ma'lumotlaringizni 'username:password' formatida yuboring:\n\nMasalan: ishonch_user:parol123",
        reply_markup=ReplyKeyboardRemove()
    )

@liker_router.message(BotState.waiting_for_credentials)
async def process_credentials(message: Message, state: FSMContext) -> None:
    if " " in message.text:
        await message.answer("Xatolik! Probel bo'lmasligi kerak.\nFormat: 'username:password'")
        return

    parts = message.text.split(":")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        await message.answer("Xatolik! 'username:password' ko'rinishida yuboring.")
        return
        
    username, password = parts[0], parts[1]
    status_message = await message.answer("Instagramga kirish harakat qilinmoqda...")
    
    success, error_msg = await login_and_save_session(message.from_user.id, username, password)
    
    if success:
        await state.set_state(BotState.ready_for_links)
        await status_message.edit_text("Instagram ulandi! Endi post havolasini yuboring.")
    else:
        # Status xabarini o'chiramiz
        try:
            await status_message.delete()
        except Exception:
            pass

        # Qayta urinish uchun /start tugmasi
        start_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="/start")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )

        # Agar xatolik rasmi tushgan bo'lsa yuboramiz
        if os.path.exists("login_error.png"):
            error_photo = FSInputFile("login_error.png")
            try:
                await message.answer_photo(
                    photo=error_photo, 
                    caption="⚠️ Instagram ekranida mana bu holat yuz berdi:"
                )
                os.remove("login_error.png")
            except Exception as e:
                print(f"Rasm yuborishda xatolik: {e}")

        # Holatni (state) tozalaymiz, foydalanuvchi /start orqali qayta boshlashi oson bo'ladi
        await state.clear()
        
        await message.answer(
            f"❌ **Kirishda xatolik yuz berdi!**\n\n"
            f"⚠️ *Xatolik:* {error_msg}\n\n"
            f"Qaytadan urinish uchun quyidagi **/start** tugmasini bosing:",
            reply_markup=start_keyboard,
            parse_mode="Markdown"
        )
            
@liker_router.message(BotState.ready_for_links)
async def handle_instagram_link(message: Message) -> None:
    link = message.text.strip()
    
    if not re.match(r"(https?://)?(www\.)?instagram\.com/(p|reel|tv)/.+", link):
        await message.answer("Iltimos, faqat to'g'ri Instagram post yoki reel havolasini yuboring.")
        return
        
    status_message = await message.answer("Like bosilmoqda va screenshot olinmoqda...")
    user_id = message.from_user.id
    screenshot_path = f"screenshot_{user_id}.png"
    
    success, error_msg = await like_post_and_screenshot(user_id, link, screenshot_path)
    
    if success:
        await status_message.delete()
        photo = FSInputFile(screenshot_path)
        await message.answer_photo(photo, caption="Muvaffaqiyatli bajarildi!")
        
        if os.path.exists(screenshot_path):
            os.remove(screenshot_path)
    else:
        await status_message.edit_text(f"Xatolik yuz berdi: {error_msg}")