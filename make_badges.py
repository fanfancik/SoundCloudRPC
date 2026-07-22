"""
make_badges.py

Генерирует набор маленьких прозрачных PNG-иконок play/pause для
small_image в Discord Rich Presence.

Discord всегда обрезает small_image по кругу — поэтому иконка рисуется
сразу как сплошной круг с ровным глифом внутри и тонкой белой окантовкой
(чтобы отделяться от обложки трека), а не как фигура произвольной формы,
которая при обрезке в круг выглядит криво.

Discord умеет показывать small_image только по прямой https-ссылке
(или по имени заранее загруженного ассета в Developer Portal) —
поэтому вместо одной иконки сразу генерируется набор цветов, и нужный
выбирается через settings_menu.py -> config.json, а сама папка
assets/badges должна быть закинута (закоммичена) в GitHub-репозиторий,
чтобы ссылки вида raw.githubusercontent.com были доступны всем, а не
только тебе на компьютере.

Запуск: python make_badges.py
"""

import os

from PIL import Image, ImageDraw

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "badges")
SIZE = 256  # Discord сам ужимает картинку, с запасом ставим покрупнее
SUPERSAMPLE = 4  # рисуем в 4x и уменьшаем — края получаются гладкими

COLORS = {
    "orange": (255, 85, 0),   # фирменный цвет SoundCloud
    "red": (224, 30, 55),
    "blue": (59, 130, 246),
    "green": (34, 197, 94),
    "purple": (168, 85, 247),
    "pink": (236, 72, 153),
    "white": (255, 255, 255),
}


def _canvas():
    s = SIZE * SUPERSAMPLE
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img), s


def _finish(img):
    return img.resize((SIZE, SIZE), Image.LANCZOS)


def make_play(color_rgb):
    img, d, s = _canvas()
    r = s * 0.47
    cx = cy = s / 2
    border = s * 0.035
    # тонкая белая окантовка — чтобы кружок не сливался с обложкой
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 255))
    d.ellipse(
        [cx - r + border, cy - r + border, cx + r - border, cy + r - border],
        fill=(*color_rgb, 255),
    )
    tri_r = r * 0.46
    offset = tri_r * 0.12  # чуть сдвигаем треугольник вправо — визуально центрируем
    p1 = (cx - tri_r + offset, cy - tri_r * 1.05)
    p2 = (cx - tri_r + offset, cy + tri_r * 1.05)
    p3 = (cx + tri_r * 1.15 + offset, cy)
    d.polygon([p1, p2, p3], fill=(255, 255, 255, 255))
    return _finish(img)


def make_pause(color_rgb):
    img, d, s = _canvas()
    r = s * 0.47
    cx = cy = s / 2
    border = s * 0.035
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 255))
    d.ellipse(
        [cx - r + border, cy - r + border, cx + r - border, cy + r - border],
        fill=(*color_rgb, 255),
    )
    bar_h = r * 1.0
    bar_w = r * 0.26
    gap = r * 0.22
    for i in (-1, 1):
        bx = cx + i * (gap / 2 + bar_w / 2)
        d.rounded_rectangle(
            [bx - bar_w / 2, cy - bar_h / 2, bx + bar_w / 2, cy + bar_h / 2],
            radius=bar_w * 0.35,
            fill=(255, 255, 255, 255),
        )
    return _finish(img)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, rgb in COLORS.items():
        make_play(rgb).save(os.path.join(OUT_DIR, f"cloud_play_{name}.png"))
        make_pause(rgb).save(os.path.join(OUT_DIR, f"cloud_pause_{name}.png"))
        print(f"  сделал cloud_play_{name}.png / cloud_pause_{name}.png")
    print(f"\nГотово. Файлы лежат в: {OUT_DIR}")
    print("Не забудь закоммитить и запушить папку assets/badges в GitHub,")
    print("иначе иконки будут видны только тебе, а не друзьям в Discord.")


if __name__ == "__main__":
    main()

