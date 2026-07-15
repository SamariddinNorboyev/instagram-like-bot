# tgbot/handlers/liker.py
import os
import re
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove, FSInputFile, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from tgbot.states.bot_states import BotState
from tgbot.services import like_post_and_screenshot, login_and_save_session, submit_2fa_code_and_save

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
    if not message.text or " " in message.text:
            await message.answer("Xatolik! Probel bo'lmasligi kerak.\nFormat: 'username:password'")
            return

    parts = message.text.split(":")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        await message.answer("Xatolik! 'username:password' ko'rinishida yuboring.")
        return
        
    username, password = parts[0], parts[1]
    status_message = await message.answer("Instagramga kirish harakat qilinmoqda...")

    if not message.from_user:
            await message.answer("Xatolik! Foydalanuvchi ma'lumotlari topilmadi.")
            return
            
    success, result_msg = await login_and_save_session(message.from_user.id, username, password)

    if result_msg == "2fa_required":
        await state.set_state(BotState.waiting_for_2fa_code)
        await status_message.answer(
            "🔒 <b>Ikki bosqichli xavfsizlik (2FA) aniqlandi!</b>\n\n"
            "Sizga Instagram tomonidan yuborilgan (SMS, WhatsApp) tasdiqlash kodini yozib yuboring:",
            parse_mode="HTML"
        )

    elif success:
        await state.set_state(BotState.ready_for_links)
        await status_message.answer(
            "✨ Instagram ulandi!\n"
            "📥 Endi post yoki reel havolasini yuboring.",
            parse_mode="HTML"
        )
    else:
        # 1. Kutish xabarini o'chiramiz
        try:
            await status_message.delete()
        except Exception:
            pass

        # 2. Qayta urinish uchun /start tugmasi
        start_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="/start")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )

        # 3. Agar serverda screenshot (login_error.png) bo'lsa, yuboramiz
        if os.path.exists("login_error.png"):
            error_photo = FSInputFile("login_error.png")
            try:
                # Maxsus belgilarda xato bermasligi uchun HTML rejimiga o'tkazildi
                await message.answer_photo(
                    photo=error_photo, 
                    caption=(
                        f"❌ <b>Kirishda xatolik yuz berdi!</b>\n\n"
                        f"⚠️ <i>Tafsilot:</i> {result_msg}\n\n"
                        f"Ekran holati yuqoridagi rasmda ko'rsatilgan. "
                        f"Qayta boshlash uchun <b>/start</b> tugmasini bosing:"
                    ),
                    reply_markup=start_keyboard,
                    parse_mode="HTML"
                )
                os.remove("login_error.png")
                await state.clear()
                return
            except Exception as e:
                print(f"Rasm yuborishda xatolik yuz berdi: {e}")

        # 4. Agar rasm bo'lmasa, faqat matnli xabarni HTML formatda yuboramiz
        await state.clear()
        await message.answer(
            f"❌ <b>Kirishda xatolik yuz berdi!</b>\n\n"
            f"⚠️ <i>Tafsilot:</i> {result_msg}\n\n"
            f"Qayta boshlash uchun quyidagi <b>/start</b> tugmasini bosing:",
            reply_markup=start_keyboard,
            parse_mode="HTML"
        )
            
@liker_router.message(BotState.ready_for_links)
async def handle_instagram_link(message: Message) -> None:
    link = (message.text or "").strip()
    
    if not re.match(r"(https?://)?(www\.)?instagram\.com/(p|reel|reels|tv)/.+", link):
            await message.answer("Iltimos, faqat to'g'ri Instagram post yoki reel havolasini yuboring.")
            return
        
    status_message = await message.answer("Like bosilmoqda va screenshot olinmoqda...")
    if not message.from_user:
            await message.answer("Xatolik! Foydalanuvchi ma'lumotlari aniqlanmadi.")
            return
    user_id = message.from_user.id
    screenshot_path = f"screenshot_{user_id}.png"
    
    success, error_msg = await like_post_and_screenshot(user_id, link, screenshot_path)
    
    if success:
        await status_message.delete()
        photo = FSInputFile(screenshot_path)

        caption_text = (
            "<b>✅ Muvaffaqiyatli bajarildi!</b>\n\n"
            f"🔗 <b>Havola:</b> {link}\n"
            "📸 <i>Bajarilgan ish skrinshoti yuqorida ilova qilindi.</i>\n\n"
            "🚀 Boshqa havola yuborishingiz mumkin."
        )
        
        await message.answer_photo(
            photo=photo, 
            caption=caption_text, 
            parse_mode="HTML"
        )
        
        if os.path.exists(screenshot_path):
            os.remove(screenshot_path)
    else:
        try:
            await status_message.delete()
        except Exception:
            pass

        if os.path.exists("like_error.png"):
            error_photo = FSInputFile("like_error.png")
            await message.answer_photo(
                photo=error_photo,
                caption=f"❌ Like bosishda muammo bo'ldi: {error_msg}"
            )
            os.remove("like_error.png")
        else:
            await message.answer(f"❌ Xatolik yuz berdi: {error_msg}")

            

@liker_router.message(BotState.waiting_for_2fa_code)
async def process_2fa_code(message: Message, state: FSMContext) -> None:
    code = (message.text or "").strip()
    
    # Faqat raqamlardan iboratligini tekshiramiz (odatda 6 yoki 8 xonali raqam bo'ladi)
    if not code.isdigit() or len(code) < 6:
        await message.answer("Iltimos, faqat to'g'ri tasdiqlash kodini yuboring (masalan: 123456).")
        return
        
    status_message = await message.answer("Kod tekshirilmoqda va ulanish yakunlanmoqda...")
    if not message.from_user:
            await message.answer("Xatolik! Foydalanuvchi ma'lumotlari topilmadi.")
            return
    user_id = message.from_user.id
    
    success, error_msg = await submit_2fa_code_and_save(user_id, code)
    
    if success:
        await state.set_state(BotState.ready_for_links)
        await status_message.answer(
            "<b>✨ Tabriklaymiz! Instagram muvaffaqiyatli ulandi (2FA tasdiqlandi).</b>\n"
            "📥 Endi post yoki reel havolasini yuborishingiz mumkin.",
            parse_mode="HTML"
        )
    else:
        try:
            await status_message.delete()
        except Exception:
            pass
            
        start_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="/start")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        # Xato skrinshoti bo'lsa uni ko'rsatish
        error_file = f"login_error_{user_id}.png"
        if os.path.exists(error_file):
            error_photo = FSInputFile(error_file)
            await message.answer_photo(
                photo=error_photo,
                caption=f"❌ <b>2FA tasdiqlashda xatolik!</b>\n\n⚠️ {error_msg}",
                reply_markup=start_keyboard,
                parse_mode="HTML"
            )
            os.remove(error_file)
        else:
            await message.answer(
                f"❌ <b>Xatolik:</b> {error_msg}\n\nQayta boshlash uchun <b>/start</b> bosing.",
                reply_markup=start_keyboard,
                parse_mode="HTML"
            )
            
        await state.clear()