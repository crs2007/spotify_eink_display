"""Tiny hand-drawn bitmaps. 'X' = ink, '.' = paper."""
from __future__ import annotations

from PIL import ImageDraw

PLAY = [
    "X......",
    "XXX....",
    "XXXXX..",
    "XXXXXXX",
    "XXXXX..",
    "XXX....",
    "X......",
]

PAUSE = [
    "XX..XX.",
    "XX..XX.",
    "XX..XX.",
    "XX..XX.",
    "XX..XX.",
    "XX..XX.",
    "XX..XX.",
]

NOTE = [
    "...XXXXXXXX",
    "...XXXXXXXX",
    "...X......X",
    "...X......X",
    "...X......X",
    "...X......X",
    "...X......X",
    ".XXX....XXX",
    "XXXX...XXXX",
    "XXXX...XXXX",
    ".XX.....XX.",
]

NOTE_SMALL = [
    "..XXXXX",
    "..X...X",
    "..X...X",
    "..X...X",
    "XXX.XXX",
    "XXX.XXX",
    "XX..XX.",
]


def draw_icon(d: ImageDraw.ImageDraw, rows: list[str], x: int, y: int, color: int, scale: int = 1) -> None:
    for ry, row in enumerate(rows):
        for rx, c in enumerate(row):
            if c == "X":
                x0, y0 = x + rx * scale, y + ry * scale
                d.rectangle((x0, y0, x0 + scale - 1, y0 + scale - 1), fill=color)


def icon_size(rows: list[str], scale: int = 1) -> tuple[int, int]:
    return len(rows[0]) * scale, len(rows) * scale
