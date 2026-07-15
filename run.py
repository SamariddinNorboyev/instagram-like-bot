# botni ishga tushiruvchi asosiy fayl
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from tgbot.config import BOT_TOKEN
from tgbot.handlers.start import start_router
from tgbot.handlers.liker import liker_router

logging.basicConfig(level=logging.INFO)

async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    
    redis_client = Redis.from_url("redis://localhost:6379")
    storage = RedisStorage(redis=redis_client)
    
    dp = Dispatcher(storage=storage)

    dp.include_router(start_router)
    dp.include_router(liker_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")