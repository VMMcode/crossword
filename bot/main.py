"""Точка входа бота."""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import config
from bot.database.models import init_db
from bot.handlers import common
from bot.handlers import game
from bot.handlers import admin
from bot.services.llm import init_llm
from bot.services.scheduler import start_scheduler, stop_scheduler


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )
    logger = logging.getLogger(__name__)

    await init_db()
    init_llm()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    dp.include_router(common.router)
    dp.include_router(game.router)
    dp.include_router(admin.router)

    start_scheduler(bot)

    logger.info("Бот запускается...")
    me = await bot.get_me()
    logger.info(f"Запущен как @{me.username} (id={me.id})")

    try:
        await dp.start_polling(bot)
    finally:
        stop_scheduler()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\nБот остановлен")