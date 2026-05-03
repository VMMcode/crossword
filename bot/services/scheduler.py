"""Расписание автоматических вопросов через APScheduler."""
import logging

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config import config

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _scheduled_question(bot) -> None:
    from bot.services.game import send_question
    logger.info("Расписание: отправляю вопрос")
    await send_question(bot)


async def _reset_week(bot) -> None:
    from bot.database.repo import reset_week_scores
    logger.info("Сброс недельного рейтинга")
    await reset_week_scores()
    if config.chat_id:
        await bot.send_message(
            config.chat_id,
            "📅 Недельный рейтинг обнулён. Новая неделя — новые победы! 🏆",
        )


def start_scheduler(bot) -> None:
    global _scheduler
    tz = pytz.timezone(config.timezone)

    _scheduler = AsyncIOScheduler(timezone=tz)

    # Вопросы по расписанию: 10:00, 13:00, 16:00, 19:00, 22:00 МСК
    for hour in [10, 13, 16, 19, 22]:
        _scheduler.add_job(
            _scheduled_question,
            trigger="cron",
            hour=hour,
            minute=0,
            args=[bot],
            id=f"question_{hour}",
        )

    # Сброс недельного рейтинга — каждый понедельник в 00:00
    _scheduler.add_job(
        _reset_week,
        trigger="cron",
        day_of_week="mon",
        hour=0,
        minute=0,
        args=[bot],
        id="reset_week",
    )

    _scheduler.start()
    logger.info("Планировщик запущен (10:00, 13:00, 16:00, 19:00, 22:00 МСК)")


def stop_scheduler() -> None:
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()