"""Игровые команды: /next, /кроссворд, ответы реплаем."""
import logging
from io import BytesIO

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile

from bot.config import config
from bot.database import repo
from bot.services.game import send_question, check_answer
from bot.services.renderer import render_crossword

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("next"))
async def cmd_question(message: Message, bot: Bot) -> None:
    """Запросить следующий вопрос вне расписания."""
    sent = await send_question(bot)
    if not sent:
        await message.answer("Не удалось отправить вопрос. Попробуй позже.")


@router.message(Command("crossword"))
async def cmd_crossword(message: Message) -> None:
    """Показать текущую сетку кроссворда."""
    result = await repo.get_crossword()
    if not result:
        await message.answer("Кроссворд ещё не создан. Напиши /next чтобы начать!")
        return

    cw, solved = result
    img_bytes = render_crossword(cw, solved_words=solved)
    photo = BufferedInputFile(img_bytes, filename="crossword.png")

    total = len(cw.words)
    done = len(solved)

    await message.answer_photo(
        photo=photo,
        caption=(
            f"🧩 <b>Тема: {cw.topic}</b>\n"
            f"Угадано: {done}/{total} слов\n\n"
            f"Отвечай реплаем на сообщение с вопросом 👆"
        ),
        parse_mode="HTML",
    )


@router.message(Command("top"))
async def cmd_top(message: Message) -> None:
    players = await repo.get_top()
    from bot.utils.text import format_top
    await message.answer(format_top(players, "🏆 Общий рейтинг"), parse_mode="HTML")


@router.message(Command("week"))
async def cmd_week(message: Message) -> None:
    players = await repo.get_top_week()
    from bot.utils.text import format_top
    await message.answer(format_top(players, "📅 Рейтинг за неделю"), parse_mode="HTML")


@router.message(Command("new"))
async def cmd_new_public(message: Message, bot: Bot) -> None:
    """Новый кроссворд — доступно всем."""
    await message.answer("⏳ Генерирую новый кроссворд...")
    from bot.services.game import generate_new_crossword
    cw = await generate_new_crossword()
    if not cw:
        await message.answer("❌ Не удалось сгенерировать кроссворд. Попробуй ещё раз.")
        return
    await message.answer(
        f"✅ Новый кроссворд готов!\nТема: <b>{cw.topic}</b>, {len(cw.words)} слов",
        parse_mode="HTML",
    )
    await send_question(bot)


@router.message(Command("skip"))
async def cmd_skip(message: Message, bot: Bot) -> None:
    """Пропустить текущий вопрос и перейти к следующему."""
    word_number = await repo.get_active_question()
    if word_number is None:
        await message.answer("Сейчас нет активного вопроса. Напиши /next")
        return

    result = await repo.get_crossword()
    if not result:
        return
    cw, solved = result

    pw = next((w for w in cw.words if w.number == word_number), None)
    await repo.clear_active_question()

    skip_text = f"⏭ Вопрос пропущен. Слово было: <b>{pw.word}</b>" if pw else "⏭ Вопрос пропущен."
    await message.answer(skip_text, parse_mode="HTML")

    # Ищем следующий неугаданный (пропуская текущий)
    next_num = None
    for w in sorted(cw.words, key=lambda x: x.number):
        if w.number not in solved and w.number != word_number:
            next_num = w.number
            break

    if next_num:
        await send_question(bot, word_number=next_num)
    else:
        await message.answer("Больше нет доступных вопросов. Напиши /next чтобы получить новый.")


@router.message(
    F.reply_to_message,
    F.reply_to_message.from_user.is_bot == True,
    F.text,
)
async def handle_reply(message: Message, bot: Bot) -> None:
    """Перехватываем реплаи на сообщения бота — проверяем как ответ на вопрос."""
    await check_answer(message, bot)