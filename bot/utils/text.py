"""Утилиты для работы с текстом."""


def normalize(text: str) -> str:
    """Нормализует ответ: верхний регистр, ё→е."""
    return text.strip().upper().replace("Ё", "Е")


def make_mask(word: str, solved_cells: set[tuple[int, int]], row: int, col: int, direction: str) -> str:
    """
    Формирует маску слова.
    Открытые буквы (из пересечений с угаданными словами) показываются,
    остальные — заменяются на ●.
    """
    mask = []
    for i, ch in enumerate(word):
        r = row + (i if direction != "H" else 0)
        c = col + (i if direction == "H" else 0)
        if (r, c) in solved_cells:
            mask.append(ch)
        else:
            mask.append("●")
    return "".join(mask)


def format_top(players: list[dict], title: str) -> str:
    if not players:
        return f"<b>{title}</b>\n\nПока никто не набрал очков 🤷"

    lines = [f"<b>{title}</b>\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, p in enumerate(players):
        if p["score"] == 0:
            continue
        medal = medals[i] if i < 3 else f"{i + 1}."
        name = p["first_name"] or p["username"] or "Аноним"
        lines.append(f"{medal} {name} — <b>{p['score']}</b> очков")

    return "\n".join(lines) if len(lines) > 1 else f"<b>{title}</b>\n\nПока никто не набрал очков 🤷"