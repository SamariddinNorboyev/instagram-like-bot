# /start va rozilik olish handleri
import os
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from tgbot.states.bot_states import BotState
from tgbot.config import COOKIES_DIR

start_router = Router()

def get_agreement_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Ha"), KeyboardButton(text="Yo'q")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_restart_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="/start")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

@start_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        await message.answer("Xatolik! Foydalanuvchi ma'lumotlari aniqlanmadi.")
        return
    user_id = message.from_user.id
    cookie_path = f"{COOKIES_DIR}/{user_id}.json"
    
    if os.path.exists(cookie_path):
        await state.set_state(BotState.ready_for_links)
        await message.answer("Siz allaqachon ulanishni amalga oshirgansiz! Menga post havolasini yuboring.")
        return

    await state.set_state(BotState.waiting_for_agreement)
    await message.answer(
        "Assalomu alaykum!\nIshonch Instagram Liker botiga xush kelibsiz. Ma'lumotlaringiz saqlanishiga rozimisiz?",
        reply_markup=get_agreement_keyboard()
    )

@start_router.message(BotState.waiting_for_agreement, F.text.lower() == "yo'q")
async def agreement_no(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Afsuski, boshqa yo'limiz yo'q. Xizmatdan foydalanish uchun rozilik berishingiz kerak.\n\nQayta boshlash:",
        reply_markup=get_restart_keyboard()
    )