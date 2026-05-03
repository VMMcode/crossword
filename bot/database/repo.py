"""Репозиторий — все запросы к БД."""
import json
import logging
from dataclasses import asdict
from typing import Optional

import aiosqlite

from bot.config import config
from bot.services.crossword import CrosswordGrid, PlacedWord, HORIZONTAL, VERTICAL

logger = logging.getLogger(__name__)


# ─── Сериализация/десериализация CrosswordGrid ───────────────────────────────

def _cw_to_dict(cw: CrosswordGrid) -> dict:
    return {
        "topic": cw.topic,
        "rows": cw.rows,
        "cols": cw.cols,
        "grid": cw.grid,
        "words": [
            {
                "word": w.word,
                "clue": w.clue,
                "row": w.row,
                "col": w.col,
                "direction": w.direction,
                "number": w.number,
            }
            for w in cw.words
        ],
    }


def _dict_to_cw(d: dict) -> CrosswordGrid:
    words = [
        PlacedWord(
            word=w["word"],
            clue=w["clue"],
            row=w["row"],
            col=w["col"],
            direction=w["direction"],
            number=w["number"],
        )
        for w in d["words"]
    ]
    cw = CrosswordGrid(
        topic=d["topic"],
        words=words,
        rows=d["rows"],
        cols=d["cols"],
    )
    cw.grid = d["grid"]
    return cw


# ─── Кроссворд ────────────────────────────────────────────────────────────────

async def save_crossword(cw: CrosswordGrid) -> None:
    async with aiosqlite.connect(config.database_path) as db:
        await db.execute(
            "INSERT OR REPLACE INTO crossword (id, topic, data, solved) VALUES (1, ?, ?, '[]')",
            (cw.topic, json.dumps(_cw_to_dict(cw), ensure_ascii=False)),
        )
        await db.execute("DELETE FROM active_question")
        await db.commit()


async def get_crossword() -> Optional[tuple[CrosswordGrid, set[int]]]:
    """Возвращает (CrosswordGrid, solved_set) или None."""
    async with aiosqlite.connect(config.database_path) as db:
        async with db.execute("SELECT data, solved FROM crossword WHERE id = 1") as cur:
            row = await cur.fetchone()
    if not row:
        return None
    cw = _dict_to_cw(json.loads(row[0]))
    solved = set(json.loads(row[1]))
    return cw, solved


async def mark_word_solved(word_number: int) -> set[int]:
    """Помечает слово как угаданное, возвращает обновлённый set."""
    async with aiosqlite.connect(config.database_path) as db:
        async with db.execute("SELECT solved FROM crossword WHERE id = 1") as cur:
            row = await cur.fetchone()
        if not row:
            return set()
        solved = set(json.loads(row[0]))
        solved.add(word_number)
        await db.execute(
            "UPDATE crossword SET solved = ? WHERE id = 1",
            (json.dumps(list(solved)),),
        )
        await db.commit()
    return solved


# ─── Активный вопрос ─────────────────────────────────────────────────────────

async def set_active_question(word_number: int) -> None:
    async with aiosqlite.connect(config.database_path) as db:
        await db.execute(
            "INSERT OR REPLACE INTO active_question (id, word_number) VALUES (1, ?)",
            (word_number,),
        )
        await db.commit()


async def get_active_question() -> Optional[int]:
    async with aiosqlite.connect(config.database_path) as db:
        async with db.execute("SELECT word_number FROM active_question WHERE id = 1") as cur:
            row = await cur.fetchone()
    return row[0] if row else None


async def clear_active_question() -> None:
    async with aiosqlite.connect(config.database_path) as db:
        await db.execute("DELETE FROM active_question")
        await db.commit()


# ─── Игроки и очки ───────────────────────────────────────────────────────────

async def add_score(user_id: int, username: str, first_name: str, points: int) -> int:
    """Добавляет очки игроку, возвращает новый total."""
    async with aiosqlite.connect(config.database_path) as db:
        await db.execute(
            """
            INSERT INTO players (user_id, username, first_name, score_total, score_week)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username    = excluded.username,
                first_name  = excluded.first_name,
                score_total = score_total + excluded.score_total,
                score_week  = score_week  + excluded.score_week,
                updated_at  = datetime('now')
            """,
            (user_id, username, first_name, points, points),
        )
        await db.commit()
        async with db.execute(
            "SELECT score_total FROM players WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
    return row[0] if row else points


async def get_top(limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(config.database_path) as db:
        async with db.execute(
            "SELECT first_name, username, score_total FROM players ORDER BY score_total DESC LIMIT ?",
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
    return [{"first_name": r[0], "username": r[1], "score": r[2]} for r in rows]


async def get_top_week(limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(config.database_path) as db:
        async with db.execute(
            "SELECT first_name, username, score_week FROM players ORDER BY score_week DESC LIMIT ?",
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
    return [{"first_name": r[0], "username": r[1], "score": r[2]} for r in rows]


async def reset_week_scores() -> None:
    async with aiosqlite.connect(config.database_path) as db:
        await db.execute("UPDATE players SET score_week = 0")
        await db.commit()


async def reset_all_scores() -> None:
    async with aiosqlite.connect(config.database_path) as db:
        await db.execute("UPDATE players SET score_total = 0, score_week = 0")
        await db.commit()