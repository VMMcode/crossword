"""Алгоритм сборки сетки кроссворда из списка слов."""
import logging
import random
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

HORIZONTAL = "H"
VERTICAL = "V"


@dataclass
class PlacedWord:
    word: str
    clue: str
    row: int       # строка верхнего левого угла
    col: int       # столбец верхнего левого угла
    direction: str  # H или V
    number: int    # номер по порядку


@dataclass
class CrosswordGrid:
    topic: str
    words: list[PlacedWord]
    rows: int
    cols: int
    # Сетка букв: grid[row][col] = буква или None
    grid: list[list[str | None]] = field(default_factory=list)

    def __post_init__(self):
        if not self.grid:
            self.grid = [[None] * self.cols for _ in range(self.rows)]
            for w in self.words:
                for i, ch in enumerate(w.word):
                    if w.direction == HORIZONTAL:
                        self.grid[w.row][w.col + i] = ch
                    else:
                        self.grid[w.row + i][w.col] = ch

    def get_letter(self, row: int, col: int) -> str | None:
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.grid[row][col]
        return None


def _find_intersections(
    placed: list[PlacedWord],
    candidate: str,
) -> list[tuple[int, int, int, int, str]]:
    """
    Ищем все позиции куда можно поставить candidate,
    пересекаясь с уже размещёнными словами.

    Возвращает список (row, col, direction, intersect_count, ...).
    """
    placements = []

    for pw in placed:
        for i, ch in enumerate(pw.word):
            # Ищем эту букву в кандидате
            for j, cch in enumerate(candidate):
                if ch != cch:
                    continue

                # pw горизонтальное -> кандидат вертикальный
                if pw.direction == HORIZONTAL:
                    row = pw.row - j
                    col = pw.col + i
                    direction = VERTICAL
                else:
                    row = pw.row + i
                    col = pw.col - j
                    direction = HORIZONTAL

                placements.append((row, col, direction, 1))

    return placements


def _can_place(
    grid: list[list[str | None]],
    rows: int,
    cols: int,
    word: str,
    row: int,
    col: int,
    direction: str,
) -> bool:
    """Проверяем, можно ли разместить слово без конфликтов."""
    length = len(word)

    # Выходит за границы
    if direction == HORIZONTAL:
        if col < 0 or col + length > cols:
            return False
        if row < 0 or row >= rows:
            return False
    else:
        if row < 0 or row + length > rows:
            return False
        if col < 0 or col >= cols:
            return False

    # Проверяем каждую клетку
    for i, ch in enumerate(word):
        r = row + (i if direction == VERTICAL else 0)
        c = col + (i if direction == HORIZONTAL else 0)

        cell = grid[r][c]

        if cell is None:
            # Клетка свободна — проверяем соседей перпендикулярно
            if direction == HORIZONTAL:
                # Выше и ниже не должно быть букв (если это не пересечение)
                above = grid[r - 1][c] if r > 0 else None
                below = grid[r + 1][c] if r < rows - 1 else None
                if above is not None or below is not None:
                    # Допускаем только если это пересечение
                    return False
            else:
                left = grid[r][c - 1] if c > 0 else None
                right = grid[r][c + 1] if c < cols - 1 else None
                if left is not None or right is not None:
                    return False
        elif cell != ch:
            # Буква не совпадает
            return False

    # Проверяем что перед началом и после конца нет букв (слова не слипаются)
    if direction == HORIZONTAL:
        before = grid[row][col - 1] if col > 0 else None
        after = grid[row][col + length] if col + length < cols else None
    else:
        before = grid[row - 1][col] if row > 0 else None
        after = grid[row + length][col] if row + length < rows else None

    if before is not None or after is not None:
        return False

    return True


def _place_word(
    grid: list[list[str | None]],
    word: str,
    row: int,
    col: int,
    direction: str,
) -> None:
    for i, ch in enumerate(word):
        r = row + (i if direction == VERTICAL else 0)
        c = col + (i if direction == HORIZONTAL else 0)
        grid[r][c] = ch


def build_crossword(
    words_data: list[dict],
    topic: str,
    grid_size: int = 15,
    target_words: int = 8,
    max_attempts: int = 5,
) -> CrosswordGrid | None:
    """
    Собирает кроссворд из списка слов.
    Возвращает CrosswordGrid или None если не удалось.
    """
    # Сортируем по длине (длинные первыми — легче строить)
    candidates = sorted(words_data, key=lambda x: len(x["word"]), reverse=True)

    for attempt in range(max_attempts):
        random.shuffle(candidates[:5])  # немного рандомим первые слова
        grid = [[None] * grid_size for _ in range(grid_size)]
        placed: list[PlacedWord] = []

        # Первое слово — горизонтально в центре
        first = candidates[0]
        fw = first["word"]
        start_row = grid_size // 2
        start_col = (grid_size - len(fw)) // 2

        _place_word(grid, fw, start_row, start_col, HORIZONTAL)
        placed.append(PlacedWord(
            word=fw,
            clue=first["clue"],
            row=start_row,
            col=start_col,
            direction=HORIZONTAL,
            number=1,
        ))

        # Пробуем добавить остальные слова
        for item in candidates[1:]:
            if len(placed) >= target_words:
                break

            word = item["word"]
            placements = _find_intersections(placed, word)

            if not placements:
                continue

            random.shuffle(placements)
            placed_ok = False

            for row, col, direction, _ in placements:
                if _can_place(grid, grid_size, grid_size, word, row, col, direction):
                    _place_word(grid, word, row, col, direction)
                    placed.append(PlacedWord(
                        word=word,
                        clue=item["clue"],
                        row=row,
                        col=col,
                        direction=direction,
                        number=len(placed) + 1,
                    ))
                    placed_ok = True
                    break

        if len(placed) >= 5:
            # Обрезаем сетку до минимального bbox
            used_rows = [r for r in range(grid_size) if any(grid[r][c] for c in range(grid_size))]
            used_cols = [c for c in range(grid_size) if any(grid[r][c] for r in range(grid_size))]

            min_r, max_r = min(used_rows), max(used_rows)
            min_c, max_c = min(used_cols), max(used_cols)

            # Добавляем padding 1 клетка
            min_r = max(0, min_r - 1)
            min_c = max(0, min_c - 1)
            max_r = min(grid_size - 1, max_r + 1)
            max_c = min(grid_size - 1, max_c + 1)

            new_rows = max_r - min_r + 1
            new_cols = max_c - min_c + 1

            # Пересчитываем координаты слов
            for pw in placed:
                pw.row -= min_r
                pw.col -= min_c

            cropped_grid = [
                [grid[r][c] for c in range(min_c, max_c + 1)]
                for r in range(min_r, max_r + 1)
            ]

            cw = CrosswordGrid(
                topic=topic,
                words=placed,
                rows=new_rows,
                cols=new_cols,
            )
            cw.grid = cropped_grid

            logger.info(
                f"Кроссворд собран: {len(placed)} слов, "
                f"сетка {new_rows}x{new_cols}, попытка {attempt + 1}"
            )
            return cw

        logger.warning(f"Попытка {attempt + 1}: разместили только {len(placed)} слов, пробуем снова")

    logger.error("Не удалось собрать кроссворд за все попытки")
    return None