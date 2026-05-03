"""Базовые команды бота"""
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привет! Я бот-кроссворд 🧩\n\n"
        "Я генерирую кроссворды и кидаю в чат вопросы по расписанию "
        "(в 10:00, 13:00, 16:00, 19:00 и 22:00 МСК).\n\n"
        "Чтобы ответить — пиши <b>реплаем</b> на сообщение с вопросом.\n\n"
        "Команды: /rules"
    )


@router.message(Command("rules", "help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "<b>Как играть:</b>\n"
        "Бот кидает вопрос с маской слова (например <code>●У●А●●</code>).\n"
        "Отвечай <b>реплаем</b> — кто первый правильно ответит, тот забирает очки "
        "(очки = длина слова).\n\n"
        "<b>Команды для всех:</b>\n"
        "/next — попросить следующий вопрос\n"
        "/кроссворд — показать сетку с прогрессом\n"
        "/топ — общий рейтинг\n"
        "/неделя — рейтинг за неделю\n"
        "/rules — это сообщение"
    )


@router.message(Command("chatid"))
async def cmd_chatid(message: Message) -> None:
    """Служебная команда чтобы узнать ID чата для конфига."""
    await message.answer(
        f"ID этого чата: <code>{message.chat.id}</code>\n"
        f"Тип: {message.chat.type}\n\n"
        f"Скопируй ID в .env как <code>CHAT_ID</code>"
    )