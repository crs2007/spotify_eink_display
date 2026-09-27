"""Text helpers: fonts, title cleanup, bidi (Hebrew), wrapping and ellipsis."""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from bidi.algorithm import get_display
from PIL import ImageFont

FONT_PATH = Path(__file__).resolve().parent.parent / "fonts" / "Heebo.ttf"
ELLIPSIS = "…"

REGULAR = 400
MEDIUM = 500
BOLD = 700


@lru_cache(maxsize=32)
def font(size: int, weight: int = REGULAR) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONT_PATH), size)
    f.set_variation_by_axes([weight])
    return f


# -- cleanup ------------------------------------------------------------------
_CLEAN = [
    re.compile(r"\s+-\s+(?:\d{4}\s+)?Remaster(?:ed)?(?:\s+\d{4})?(?:\s+Version)?\s*$", re.I),
    re.compile(r"\s*[(\[](?:\d{4}\s+)?Remaster(?:ed)?[^)\]]*[)\]]", re.I),
    re.compile(r"\s+-\s+(?:Radio Edit|Single Version|Album Version|Mono|Stereo)\s*$", re.I),
    re.compile(r"\s*[(\[](?:Radio Edit|Single Version|Album Version)[)\]]", re.I),
]
_DROP_CATEGORIES = {"So", "Cs", "Co", "Cn", "Cc"}
_DROP_CHARS = {"‍", "️", "︎"}


def clean_title(s: str) -> str:
    for rx in _CLEAN:
        s = rx.sub("", s)
    return s.strip()


def sanitize(s: str) -> str:
    """Drop emoji/symbols the font can't draw; collapse whitespace."""
    out = []
    for ch in s:
        if ch in _DROP_CHARS or unicodedata.category(ch) in _DROP_CATEGORIES:
            continue
        out.append(ch)
    return " ".join("".join(out).split())


# -- direction ----------------------------------------------------------------
def is_rtl(s: str) -> bool:
    """Base direction from the first strong character (UAX#9 P2)."""
    for ch in s:
        d = unicodedata.bidirectional(ch)
        if d in ("R", "AL"):
            return True
        if d == "L":
            return False
    return False


def visual(s: str, rtl: bool) -> str:
    if not any(unicodedata.bidirectional(c) in ("R", "AL") for c in s):
        return s
    return get_display(s, base_dir="R" if rtl else "L")


# -- measuring / wrapping -----------------------------------------------------
def width(s: str, f: ImageFont.FreeTypeFont) -> float:
    return f.getlength(s)


def ellipsize(s: str, f, max_w: float, rtl: bool) -> str:
    """Cut the *logical* end and add '…' (visually lands left for RTL)."""
    if width(visual(s, rtl), f) <= max_w:
        return s
    while s and width(visual(s.rstrip() + ELLIPSIS, rtl), f) > max_w:
        s = s[:-1]
    return s.rstrip() + ELLIPSIS


def wrap(s: str, f, max_w: float, max_lines: int) -> list[str]:
    """Greedy word wrap in logical order; last line ellipsized. Returns logical lines."""
    rtl = is_rtl(s)
    words = s.split(" ")
    lines: list[str] = []
    cur = ""
    i = 0
    while i < len(words):
        w = words[i]
        trial = f"{cur} {w}" if cur else w
        if width(visual(trial, rtl), f) <= max_w:
            cur = trial
            i += 1
            continue
        if not cur:  # a single word wider than the line: hard-break it
            cut = len(w)
            while cut > 1 and width(visual(w[:cut], rtl), f) > max_w:
                cut -= 1
            lines.append(w[:cut])
            words[i] = w[cut:]
        else:
            lines.append(cur)
            cur = ""
        if len(lines) == max_lines:
            break
    if len(lines) < max_lines and cur:
        lines.append(cur)
        cur = ""
        i = len(words)
    rest = " ".join(([cur] if cur else []) + words[i:]).strip()
    if rest and lines:
        lines[-1] = ellipsize(lines[-1] + " " + rest, f, max_w, rtl)
    return lines[:max_lines]
