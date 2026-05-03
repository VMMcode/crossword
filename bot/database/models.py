"""Схема базы данных и инициализация."""
import aiosqlite
from bot.config import config

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS players (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    first_name  TEXT,
    score_total INTEGER DEFAULT 0,
    score_week  INTEGER DEFAULT 0,
    updated_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS crossword (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    topic       TEXT NOT NULL,
    data        TEXT NOT NULL,   -- JSON: весь CrosswordGrid
    solved      TEXT DEFAULT '[]',  -- JSON: список номеров угаданных слов
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS active_question (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    word_number INTEGER NOT NULL,
    asked_at    TEXT DEFAULT (datetime('now'))
);
"""


async def init_db() -> None:
    async with aiosqlite.connect(config.database_path) as db:
        await db.executescript(CREATE_TABLES)
        await db.commit()