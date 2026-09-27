"""Cover art: fetch + disk cache, tone, and dither to the panel's W/K/R inks."""
from __future__ import annotations

import colorsys
import hashlib
import io
import logging
from pathlib import Path

from PIL import Image, ImageOps

from .palette import BLACK, RED, WHITE

log = logging.getLogger(__name__)

ART_SIZE = 122
CACHE_MAX_FILES = 50

# Target colours used for error-diffusion distance (approximate panel inks).
_INKS_BW = [(255, 255, 255, WHITE), (0, 0, 0, BLACK)]
_INKS_BWR = _INKS_BW + [(200, 30, 30, RED)]


# -- fetching -----------------------------------------------------------------
async def fetch(session, url: str, cache_dir: Path, headers: dict | None = None) -> Image.Image | None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / (hashlib.sha1(url.encode()).hexdigest() + ".img")
    if path.exists():
        path.touch()
        data = path.read_bytes()
    else:
        try:
            async with session.get(url, headers=headers or {}, timeout=10) as r:
                if r.status != 200:
                    log.warning("art fetch %s → HTTP %s", url, r.status)
                    return None
                data = await r.read()
        except Exception as e:  # network errors must never break a publish
            log.warning("art fetch failed: %s", e)
            return None
        path.write_bytes(data)
        _prune(cache_dir)
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        return img.convert("RGB")
    except Exception as e:
        log.warning("art decode failed: %s", e)
        path.unlink(missing_ok=True)
        return None


def _prune(cache_dir: Path) -> None:
    files = sorted(cache_dir.glob("*.img"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in files[CACHE_MAX_FILES:]:
        p.unlink(missing_ok=True)


# -- processing ---------------------------------------------------------------
def square(img: Image.Image, size: int = ART_SIZE) -> Image.Image:
    return ImageOps.fit(img.convert("RGB"), (size, size), Image.LANCZOS, centering=(0.5, 0.5))


def red_ratio(img: Image.Image) -> float:
    """Share of clearly red pixels (hue within ±20°, S>0.45, V>0.35)."""
    small = img.convert("RGB").resize((48, 48), Image.BILINEAR)
    px = list(small.getdata())
    n = 0
    for r, g, b in px:
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s > 0.45 and v > 0.35 and (h <= 20 / 360 or h >= 340 / 360):
            n += 1
    return n / len(px)


def _tone(img: Image.Image) -> Image.Image:
    img = ImageOps.autocontrast(img, cutoff=1)
    lut = [round(255 * (i / 255) ** 0.9) for i in range(256)]
    return img.point(lut * len(img.getbands()))


def _atkinson(pixels: list[list[float]], w: int, h: int, inks) -> list[int]:
    """Atkinson error diffusion over RGB floats; returns ink index per pixel."""
    out = [WHITE] * (w * h)
    for y in range(h):
        for x in range(w):
            r, g, b = pixels[y * w + x]
            best = min(inks, key=lambda k: (k[0] - r) ** 2 + (k[1] - g) ** 2 + (k[2] - b) ** 2)
            out[y * w + x] = best[3]
            er, eg, eb = (r - best[0]) / 8, (g - best[1]) / 8, (b - best[2]) / 8
            for dx, dy in ((1, 0), (2, 0), (-1, 1), (0, 1), (1, 1), (0, 2)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and ny < h:
                    p = pixels[ny * w + nx]
                    pixels[ny * w + nx] = (p[0] + er, p[1] + eg, p[2] + eb)
    return out


def dither(img: Image.Image, palette_mode: str = "auto") -> Image.Image:
    """RGB cover → 'P' image of ink indices (WHITE/BLACK/RED), ART_SIZE square."""
    sq = square(img)
    use_red = palette_mode == "bwr" or (palette_mode == "auto" and red_ratio(sq) >= 0.08)
    if use_red:
        src = _tone(sq)
        inks = _INKS_BWR
    else:
        g = _tone(sq.convert("L"))
        src = Image.merge("RGB", (g, g, g))
        inks = _INKS_BW
    pixels = [tuple(float(c) for c in p) for p in src.getdata()]
    idx = _atkinson(pixels, ART_SIZE, ART_SIZE, inks)
    out = Image.new("P", (ART_SIZE, ART_SIZE), WHITE)
    out.putdata(idx)
    return out
