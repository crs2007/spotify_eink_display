"""Screen layouts on a 250×122 landscape 'P' canvas (ink indices W/K/R).

    x:0          121 126                                  247
      ┌────────────┐ ┌──────────────────────────────────────┐
      │            │ │ ▶ NOW PLAYING                    (R) │
      │   COVER    │ │ Title, bold, ≤2 lines            (K) │
      │  122×122   │ │ Artist, ≤2 lines                 (R) │
      │            │ │ Album, 1 line                    (K) │
      │            │ │ ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄ │
      │            │ │ ♪ Ofri                         14:32 │
      └────────────┘ └──────────────────────────────────────┘
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from PIL import Image, ImageDraw

from ..model import PAUSED, NowPlaying
from . import icons
from .art import ART_SIZE
from .palette import BLACK, RED, WHITE, attach
from .text import BOLD, MEDIUM, REGULAR, clean_title, font, is_rtl, sanitize, visual, wrap, ellipsize

W, H = 250, 122
COL_X0 = ART_SIZE + 5  # 127
COL_X1 = W - 3  # 247 (inclusive right edge)
COL_W = COL_X1 - COL_X0 + 1

LABEL_SIZE, TITLE_SIZE, ARTIST_SIZE, ALBUM_SIZE, FOOT_SIZE = 10, 15, 13, 11, 10
TITLE_STEP, ARTIST_STEP, ALBUM_STEP = 16, 14, 12
BODY_TOP = 17  # first title line top
BODY_BOTTOM = 101  # last pixel the body may use (dotted rule at 104)
RULE_Y = 104
FOOT_BASE = 117


@dataclass
class Opts:
    owner: str = "Ofri"
    clean_titles: bool = True


def new_canvas() -> Image.Image:
    img = Image.new("P", (W, H), WHITE)
    attach(img)
    return img


def _draw(img: Image.Image) -> ImageDraw.ImageDraw:
    d = ImageDraw.Draw(img)
    d.fontmode = "1"  # no anti-aliasing: every pixel is pure ink
    return d


def _line(d, s: str, f, top: int, color: int, x0: int = COL_X0, x1: int = COL_X1, align: str | None = None) -> None:
    """Draw one logical line; RTL text is right-aligned unless align is given."""
    rtl = is_rtl(s)
    v = visual(s, rtl)
    w = f.getlength(v)
    a = align or ("right" if rtl else "left")
    if a == "right":
        x = x1 + 1 - w
    elif a == "center":
        x = x0 + (x1 - x0 + 1 - w) / 2
    else:
        x = x0
    # Baseline so that Latin cap-height (~0.72 em in Heebo) starts at `top`.
    d.text((round(x), top + round(f.size * 0.75)), v, font=f, fill=color, anchor="ls")


def _dotted_rule(d, y: int, x0: int = COL_X0, x1: int = COL_X1) -> None:
    for x in range(x0, x1 + 1, 2):
        d.point((x, y), fill=BLACK)


def _footer(d, opts: Opts, now: datetime, x0: int = COL_X0, x1: int = COL_X1) -> None:
    _dotted_rule(d, RULE_Y, x0, x1)
    f = font(FOOT_SIZE, MEDIUM)
    icons.draw_icon(d, icons.NOTE_SMALL, x0, FOOT_BASE - 8, BLACK)
    name = sanitize(opts.owner)
    d.text((x0 + 10, FOOT_BASE), visual(name, is_rtl(name)), font=f, fill=BLACK, anchor="ls")
    clock = now.strftime("%H:%M")
    d.text((x1 + 1, FOOT_BASE), clock, font=f, fill=BLACK, anchor="rs")


def _fit_body(title: str, artist: str, album: str) -> list[tuple[list[str], object, int, int]]:
    """Pick the richest arrangement that fits between BODY_TOP and BODY_BOTTOM."""
    ft, fa, fb = font(TITLE_SIZE, BOLD), font(ARTIST_SIZE, REGULAR), font(ALBUM_SIZE, REGULAR)
    avail = BODY_BOTTOM - BODY_TOP + 1
    plans = [(2, 2, 1), (2, 1, 1), (2, 2, 0), (2, 1, 0), (1, 1, 0)]
    for nt, na, nb in plans:
        blocks = []
        t = wrap(title, ft, COL_W, nt) if title else []
        a = wrap(artist, fa, COL_W, na) if artist else []
        b = wrap(album, fb, COL_W, nb) if (album and nb and album.casefold() != title.casefold()) else []
        if t:
            blocks.append((t, ft, TITLE_STEP, BLACK))
        if a:
            blocks.append((a, fa, ARTIST_STEP, RED))
        if b:
            blocks.append((b, fb, ALBUM_STEP, BLACK))
        gaps = 3 * (len(blocks) - 1)
        need = sum(len(lines) * step for lines, _, step, _ in blocks) + gaps
        if need <= avail:
            return blocks
    return blocks


def _art_placeholder(img: Image.Image) -> None:
    d = _draw(img)
    d.rectangle((0, 0, ART_SIZE - 1, ART_SIZE - 1), outline=BLACK)
    w, h = icons.icon_size(icons.NOTE, 4)
    icons.draw_icon(d, icons.NOTE, (ART_SIZE - w) // 2, (ART_SIZE - h) // 2, BLACK, 4)


def render_track(np: NowPlaying, kind: str, art: Image.Image | None, opts: Opts, now: datetime) -> Image.Image:
    img = new_canvas()
    if art is not None:
        img.paste(art, (0, 0))
    else:
        _art_placeholder(img)
    d = _draw(img)

    # status label
    paused = kind == PAUSED
    icons.draw_icon(d, icons.PAUSE if paused else icons.PLAY, COL_X0, 3, RED)
    d.text((COL_X0 + 11, 10), "PAUSED" if paused else "NOW PLAYING", font=font(LABEL_SIZE, BOLD), fill=RED, anchor="ls")

    title = sanitize(np.title)
    if opts.clean_titles:
        title = clean_title(title)
    artist, album = sanitize(np.artist), sanitize(np.album)
    if opts.clean_titles:
        album = clean_title(album)

    y = BODY_TOP
    for lines, f, step, color in _fit_body(title, artist, album):
        for ln in lines:
            _line(d, ln, f, y, color)
            y += step
        y += 3
    _footer(d, opts, now)
    return img


def render_idle(last: NowPlaying | None, opts: Opts, now: datetime) -> Image.Image:
    img = new_canvas()
    d = _draw(img)
    w, h = icons.icon_size(icons.NOTE, 3)
    icons.draw_icon(d, icons.NOTE, (W - w) // 2, 10, RED, 3)
    _line(d, "Nothing playing", font(17, BOLD), 50, BLACK, 0, W - 1, "center")
    owner = sanitize(opts.owner)
    sub = f"{owner} · {now.strftime('%a %d %b')}"
    _line(d, sub, font(12, REGULAR), 72, BLACK, 0, W - 1, "center")
    if last is not None and last.has_track:
        f = font(11, REGULAR)
        t = sanitize(last.title)
        if opts.clean_titles:
            t = clean_title(t)
        s = f"Last: {t} — {sanitize(last.artist)}" if last.artist else f"Last: {t}"
        s = ellipsize(s, f, W - 16, is_rtl(s))
        _dotted_rule(d, 93, 8, W - 9)
        _line(d, s, f, 98, RED, 0, W - 1, "center")
    return img


def render_error(message: str, opts: Opts, now: datetime) -> Image.Image:
    img = new_canvas()
    d = _draw(img)
    d.rectangle((W // 2 - 14, 8, W // 2 + 13, 35), fill=RED)
    d.text((W // 2, 32), "!", font=font(26, BOLD), fill=WHITE, anchor="ms")
    _line(d, "Can't get the song", font(16, BOLD), 44, BLACK, 0, W - 1, "center")
    f = font(11, REGULAR)
    for i, ln in enumerate(wrap(sanitize(message), f, W - 20, 2)):
        _line(d, ln, f, 66 + i * 13, BLACK, 0, W - 1, "center")
    _line(d, f"{sanitize(opts.owner)} · {now.strftime('%H:%M')}", font(10, MEDIUM), 100, BLACK, 0, W - 1, "center")
    return img
