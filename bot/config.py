"""Конфигурация бота — читает переменные окружения из .env"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    bot_token: str
    admin_id: int
    chat_id: int | None
    database_path: str
    timezone: str


def load_config() -> Config:
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN не указан в .env")

    admin_id = os.getenv("ADMIN_ID")
    if not admin_id:
        raise ValueError("ADMIN_ID не указан в .env")

    chat_id_raw = os.getenv("CHAT_ID")
    chat_id = int(chat_id_raw) if chat_id_raw else None

    return Config(
        bot_token=bot_token,
        admin_id=int(admin_id),
        chat_id=chat_id,
        database_path=os.getenv("DATABASE_PATH", "crossword.db"),
        timezone=os.getenv("TIMEZONE", "Europe/Moscow"),
    )


config = load_config()