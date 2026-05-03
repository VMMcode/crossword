"""Админские команды: /new, /сброс, /тема, /стоп, /старт."""
import logging

from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import config
from bot.database import repo
from bot.services.game import generate_new_crossword, send_question

router = Router()
logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    return user_id == config.admin_id


@router.message(Command("topic"))
async def cmd_topic(message: Message, bot: Bot) -> None:
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /тема <название темы>")
        return

    topic = parts[1].strip()
    await message.answer(f"⏳ Генерирую кроссворд на тему «{topic}»...")

    from bot.services.llm import generate_words
    from bot.services.crossword import build_crossword

    words = await generate_words(topic, count=20)
    if not words:
        await message.answer("❌ Не удалось получить слова от нейросети.")
        return

    cw = build_crossword(words, topic)
    if not cw:
        await message.answer("❌ Не удалось собрать сетку кроссворда.")
        return

    await repo.save_crossword(cw)
    await message.answer(
        f"✅ Кроссворд на тему «{topic}» готов! {len(cw.words)} слов.",
        parse_mode="HTML",
    )
    await send_question(bot)


@router.message(Command("reset"))
async def cmd_reset(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await repo.reset_all_scores()
    await message.answer("✅ Все рейтинги сброшены.")


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return

    result = await repo.get_crossword()
    if not result:
        await message.answer("Кроссворда нет. Напиши /new")
        return

    cw, solved = result
    active = await repo.get_active_question()
    await message.answer(
        f"📊 <b>Статус:</b>\n"
        f"Тема: {cw.topic}\n"
        f"Слов: {len(cw.words)}, угадано: {len(solved)}\n"
        f"Активный вопрос: {active or 'нет'}\n"
        f"Chat ID: <code>{config.chat_id}</code>",
        parse_mode="HTML",
    )