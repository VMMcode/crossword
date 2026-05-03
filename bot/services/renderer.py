"""Рендер картинки кроссворда через Pillow."""
import io
import logging
from PIL import Image, ImageDraw, ImageFont

from bot.services.crossword import CrosswordGrid, HORIZONTAL

logger = logging.getLogger(__name__)

# Цвета (мягкие, не резкие)
BG_COLOR = (245, 243, 238)         # тёплый почти-белый фон страницы
CELL_EMPTY = (245, 243, 238)       # пустая клетка = фон (невидима)
CELL_ACTIVE = (255, 255, 255)      # активная клетка (буква есть) — чистый белый
CELL_SOLVED = (220, 237, 220)      # угаданная клетка — мягкий зелёный
BORDER_COLOR = (180, 175, 165)     # рамка клетки — тёплый серый
LETTER_COLOR = (45, 42, 38)        # буква — почти чёрный, тёплый
NUMBER_COLOR = (140, 130, 118)     # номер в углу — серо-коричневый
TITLE_COLOR = (90, 85, 78)         # заголовок темы

CELL_SIZE = 42       # размер клетки в пикселях
PADDING = 24         # отступ от края
NUMBER_FONT_SIZE = 10
LETTER_FONT_SIZE = 20
TITLE_FONT_SIZE = 15


def _get_font(size: int) -> ImageFont.ImageFont:
    """Пробуем загрузить системный шрифт, иначе дефолтный."""
    font_candidates = [
        "arial.ttf",
        "Arial.ttf",
        "DejaVuSans.ttf",
        "LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in font_candidates:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def render_crossword(
    cw: CrosswordGrid,
    solved_words: set[int] | None = None,
) -> bytes:
    """
    Рисует картинку кроссворда.

    solved_words — set номеров уже угаданных слов (их клетки подсвечиваются зелёным).
    Возвращает PNG как bytes.
    """
    if solved_words is None:
        solved_words = set()

    # Определяем какие клетки угаданы
    solved_cells: set[tuple[int, int]] = set()
    for pw in cw.words:
        if pw.number in solved_words:
            for i in range(len(pw.word)):
                r = pw.row + (i if pw.direction != HORIZONTAL else 0)
                c = pw.col + (i if pw.direction == HORIZONTAL else 0)
                solved_cells.add((r, c))

    # Нумерация клеток: собираем какие клетки получают номер
    numbered: dict[tuple[int, int], int] = {}
    for pw in cw.words:
        numbered[(pw.row, pw.col)] = pw.number

    # Размер картинки
    title_height = TITLE_FONT_SIZE + 20
    img_w = PADDING * 2 + cw.cols * CELL_SIZE
    img_h = PADDING + title_height + cw.rows * CELL_SIZE + PADDING

    img = Image.new("RGB", (img_w, img_h), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_letter = _get_font(LETTER_FONT_SIZE)
    font_number = _get_font(NUMBER_FONT_SIZE)
    font_title = _get_font(TITLE_FONT_SIZE)

    # Заголовок — тема
    title = f"Тема: {cw.topic}"
    draw.text((PADDING, PADDING // 2), title, font=font_title, fill=TITLE_COLOR)

    top_offset = PADDING + title_height

    # Рисуем клетки
    for row in range(cw.rows):
        for col in range(cw.cols):
            letter = cw.get_letter(row, col)
            x = PADDING + col * CELL_SIZE
            y = top_offset + row * CELL_SIZE

            if letter is None:
                # Пустая клетка — просто фон, без рамки
                continue

            # Цвет заливки
            if (row, col) in solved_cells:
                fill = CELL_SOLVED
            else:
                fill = CELL_ACTIVE

            # Рисуем клетку
            draw.rectangle(
                [x, y, x + CELL_SIZE - 1, y + CELL_SIZE - 1],
                fill=fill,
                outline=BORDER_COLOR,
                width=1,
            )

            # Номер в верхнем левом углу
            if (row, col) in numbered:
                num_str = str(numbered[(row, col)])
                draw.text((x + 2, y + 1), num_str, font=font_number, fill=NUMBER_COLOR)

            # Буква по центру клетки
            bbox = draw.textbbox((0, 0), letter, font=font_letter)
            lw = bbox[2] - bbox[0]
            lh = bbox[3] - bbox[1]
            lx = x + (CELL_SIZE - lw) // 2 - bbox[0]
            ly = y + (CELL_SIZE - lh) // 2 - bbox[1]
            draw.text((lx, ly), letter, font=font_letter, fill=LETTER_COLOR)

    # Сохраняем в bytes
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf.read()


def render_question(
    cw: CrosswordGrid,
    word_number: int,
    solved_words: set[int],
) -> bytes:
    """
    Рисует картинку кроссворда с подсветкой текущего вопроса.
    Текущее слово выделяется рамкой.
    """
    # Находим текущее слово
    current = next((pw for pw in cw.words if pw.number == word_number), None)

    if solved_words is None:
        solved_words = set()

    solved_cells: set[tuple[int, int]] = set()
    for pw in cw.words:
        if pw.number in solved_words:
            for i in range(len(pw.word)):
                r = pw.row + (i if pw.direction != HORIZONTAL else 0)
                c = pw.col + (i if pw.direction == HORIZONTAL else 0)
                solved_cells.add((r, c))

    current_cells: set[tuple[int, int]] = set()
    if current:
        for i in range(len(current.word)):
            r = current.row + (i if current.direction != HORIZONTAL else 0)
            c = current.col + (i if current.direction == HORIZONTAL else 0)
            current_cells.add((r, c))

    numbered: dict[tuple[int, int], int] = {}
    for pw in cw.words:
        numbered[(pw.row, pw.col)] = pw.number

    HIGHLIGHT_COLOR = (255, 243, 205)   # жёлтый для текущего вопроса
    HIGHLIGHT_BORDER = (210, 160, 50)

    title_height = TITLE_FONT_SIZE + 20
    img_w = PADDING * 2 + cw.cols * CELL_SIZE
    img_h = PADDING + title_height + cw.rows * CELL_SIZE + PADDING

    img = Image.new("RGB", (img_w, img_h), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_letter = _get_font(LETTER_FONT_SIZE)
    font_number = _get_font(NUMBER_FONT_SIZE)
    font_title = _get_font(TITLE_FONT_SIZE)

    title = f"Тема: {cw.topic}"
    draw.text((PADDING, PADDING // 2), title, font=font_title, fill=TITLE_COLOR)

    top_offset = PADDING + title_height

    for row in range(cw.rows):
        for col in range(cw.cols):
            letter = cw.get_letter(row, col)
            x = PADDING + col * CELL_SIZE
            y = top_offset + row * CELL_SIZE

            if letter is None:
                continue

            if (row, col) in current_cells:
                fill = HIGHLIGHT_COLOR
                outline = HIGHLIGHT_BORDER
            elif (row, col) in solved_cells:
                fill = CELL_SOLVED
                outline = BORDER_COLOR
            else:
                fill = CELL_ACTIVE
                outline = BORDER_COLOR

            draw.rectangle(
                [x, y, x + CELL_SIZE - 1, y + CELL_SIZE - 1],
                fill=fill,
                outline=outline,
                width=1,
            )

            if (row, col) in numbered:
                num_str = str(numbered[(row, col)])
                draw.text((x + 2, y + 1), num_str, font=font_number, fill=NUMBER_COLOR)

            # Буквы показываем только для угаданных клеток (не для текущего вопроса!)
            if (row, col) in solved_cells:
                bbox = draw.textbbox((0, 0), letter, font=font_letter)
                lw = bbox[2] - bbox[0]
                lh = bbox[3] - bbox[1]
                lx = x + (CELL_SIZE - lw) // 2 - bbox[0]
                ly = y + (CELL_SIZE - lh) // 2 - bbox[1]
                draw.text((lx, ly), letter, font=font_letter, fill=LETTER_COLOR)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf.read()