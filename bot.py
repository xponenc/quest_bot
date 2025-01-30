import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from handlers.hahlers_start import start_router
from handlers.handlers_payments import payment_router
from handlers.handlers_quest import quest_router
from services.loggers import logger

load_dotenv()

bot = Bot(token=os.getenv('TELEGRAM_TOKEN'))
dp = Dispatcher(storage=MemoryStorage())

dp.include_routers(
    start_router,
    quest_router,
    payment_router,
)


async def main():
    try:
        logger.info("Запуск бота...")
        await dp.start_polling(bot)
    finally:
        logger.info("Остановка бота...")
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())