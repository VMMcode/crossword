"""Игровая логика: генерация кроссворда, отправка вопросов, проверка ответов."""
import logging
from io import BytesIO

from aiogram import Bot
from aiogram.types import BufferedInputFile, Message

from bot.config import config
from bot.database import repo
from bot.services.crossword import CrosswordGrid, HORIZONTAL
from bot.services.llm import init_llm, generate_words, random_topic
from bot.services.renderer import render_question, render_crossword
from bot.utils.text import normalize, make_mask

logger = logging.getLogger(__name__)


async def generate_new_crossword() -> CrosswordGrid | None:
    """Генерирует новый кроссворд и сохраняет в БД."""
    from bot.services.crossword import build_crossword

    topic = random_topic()
    logger.info(f"Генерируем кроссворд на тему: {topic}")

    for attempt in range(3):
        words = await generate_words(topic, count=20)
        if not words:
            logger.warning(f"Попытка {attempt + 1}: Groq не вернул слов")
            continue

        cw = build_crossword(words, topic)
        if cw:
            await repo.save_crossword(cw)
            logger.info(f"Кроссворд сохранён: {len(cw.words)} слов, тема «{topic}»")
            return cw

        logger.warning(f"Попытка {attempt + 1}: не удалось собрать сетку")

    logger.error("Не удалось сгенерировать кроссворд за 3 попытки")
    return None


def _get_solved_cells(cw: CrosswordGrid, solved: set[int]) -> set[tuple[int, int]]:
    """Возвращает координаты всех клеток угаданных слов."""
    cells = set()
    for pw in cw.words:
        if pw.number in solved:
            for i in range(len(pw.word)):
                r = pw.row + (i if pw.direction != HORIZONTAL else 0)
                c = pw.col + (i if pw.direction == HORIZONTAL else 0)
                cells.add((r, c))
    return cells


def _next_question(cw: CrosswordGrid, solved: set[int]) -> int | None:
    """Возвращает номер следующего неугаданного слова."""
    for pw in sorted(cw.words, key=lambda w: w.number):
        if pw.number not in solved:
            return pw.number
    return None


async def send_question(bot: Bot, word_number: int | None = None) -> bool:
    """
    Отправляет вопрос в чат.
    Если word_number не указан — берёт следующий неугаданный.
    Возвращает True если вопрос отправлен.
    """
    if config.chat_id is None:
        logger.error("CHAT_ID не задан в конфиге")
        return False

    result = await repo.get_crossword()
    if not result:
        # Нет кроссворда — генерируем
        cw = await generate_new_crossword()
        if not cw:
            return False
        solved = set()
    else:
        cw, solved = result

    if word_number is None:
        word_number = _next_question(cw, solved)

    if word_number is None:
        # Все слова угаданы — генерируем новый
        cw = await generate_new_crossword()
        if not cw:
            return False
        solved = set()
        word_number = _next_question(cw, solved)

    if word_number is None:
        return False

    pw = next((w for w in cw.words if w.number == word_number), None)
    if not pw:
        return False

    # Сохраняем активный вопрос
    await repo.set_active_question(word_number)

    # Маска слова
    solved_cells = _get_solved_cells(cw, solved)
    mask = make_mask(pw.word, solved_cells, pw.row, pw.col, pw.direction)
    direction_str = "по горизонтали →" if pw.direction == HORIZONTAL else "по вертикали ↓"

    # Картинка с подсветкой текущего вопроса
    img_bytes = render_question(cw, word_number, solved)
    photo = BufferedInputFile(img_bytes, filename="crossword.png")

    caption = (
        f"🧩 <b>Вопрос №{word_number}</b> ({direction_str}, {len(pw.word)} букв)\n\n"
        f"<i>{pw.clue}</i>\n\n"
        f"Маска: <code>{mask}</code>\n\n"
        f"Отвечай реплаем на это сообщение 👆"
    )

    await bot.send_photo(
        chat_id=config.chat_id,
        photo=photo,
        caption=caption,
        parse_mode="HTML",
    )
    return True


async def check_answer(message: Message, bot: Bot) -> None:
    """
    Проверяет ответ пользователя (реплай на сообщение бота).
    """
    if config.chat_id is None:
        return

    # Получаем активный вопрос
    word_number = await repo.get_active_question()
    if word_number is None:
        return

    result = await repo.get_crossword()
    if not result:
        return
    cw, solved = result

    if word_number in solved:
        return

    pw = next((w for w in cw.words if w.number == word_number), None)
    if not pw:
        return

    user_answer = normalize(message.text or "")
    correct = normalize(pw.word)

    if user_answer != correct:
        await message.reply("❌")
        return

    # Верный ответ!
    user = message.from_user
    points = len(pw.word)
    total = await repo.add_score(
        user_id=user.id,
        username=user.username or "",
        first_name=user.first_name or "Аноним",
        points=points,
    )

    solved = await repo.mark_word_solved(word_number)
    await repo.clear_active_question()

    # Сообщение о победе
    name = user.first_name or user.username or "Аноним"
    remaining = len(cw.words) - len(solved)

    if remaining == 0:
        remaining_text = "\n\n🎉 <b>Кроссворд разгадан полностью!</b> Генерирую новый..."
    else:
        remaining_text = f"\n\nОсталось неразгаданных слов в кроссворде: {remaining}"

    text = (
        f"✅ <b>{name}</b> угадал(а)!\n"
        f"Слово: <b>{pw.word}</b>\n\n"
        f"🎯 +{points} очков (всего: {total})"
        f"{remaining_text}"
    )

    await message.reply(text, parse_mode="HTML")

    if remaining == 0:
        # Генерируем новый кроссворд и сразу шлём первый вопрос
        cw = await generate_new_crossword()
        if cw:
            await bot.send_message(
                chat_id=config.chat_id,
                text=f"🆕 Новый кроссворд готов! Тема: <b>{cw.topic}</b>",
                parse_mode="HTML",
            )
            await send_question(bot)
    else:
        # Автоматически шлём следующий вопрос
        await send_question(bot)