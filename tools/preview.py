"""Render every screen variant to PNG without Home Assistant or hardware.

    python tools/preview.py                 # → out/preview/*.png (1× and 4×)
    python tools/preview.py --cover a.jpg   # use a real cover for the track screens
"""
from __future__ import annotations

import argparse
import math
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "nowplaying_eink"))

from app.model import PAUSED, PLAYING, NowPlaying  # noqa: E402
from app.render import art as artmod  # noqa: E402
from app.render.layout import Opts, render_error, render_idle, render_track  # noqa: E402
from app.render.pack import pack, preview_png  # noqa: E402


def synth_cover(kind: str) -> Image.Image:
    """Stand-in covers so previews work offline."""
    img = Image.new("RGB", (300, 300))
    d = ImageDraw.Draw(img)
    if kind == "red":
        for y in range(300):
            d.line((0, y, 299, y), fill=(210, 40 + y // 6, 40))
        d.ellipse((60, 60, 240, 240), fill=(20, 20, 20))
        d.ellipse((130, 130, 170, 170), fill=(230, 220, 200))
    elif kind == "portrait":
        for y in range(300):
            for x in range(0, 300, 3):
                r = math.hypot(x - 150, y - 120)
                v = max(0, min(255, int(255 - r * 1.4)))
                d.line((x, y, x + 2, y), fill=(v, int(v * 0.85), int(v * 0.7)))
        d.rectangle((0, 250, 299, 299), fill=(30, 30, 60))
    else:  # gradient
        for x in range(300):
            d.line((x, 0, x, 299), fill=(x * 255 // 299, 120, 255 - x * 255 // 299))
        d.rectangle((40, 40, 120, 120), outline=(255, 255, 255), width=6)
    return img


FIXTURES = [
    ("en_short", NowPlaying(PLAYING, "Blinding Lights", "The Weeknd", "After Hours"), "gradient"),
    ("en_long", NowPlaying(PLAYING, "Don't Stop Me Now - Remastered 2011", "Queen", "Jazz (2011 Remaster)"), "portrait"),
    ("en_verylong", NowPlaying(PLAYING, "Supercalifragilisticexpialidocious (From \"Mary Poppins\") 🎵",
                               "Julie Andrews, Dick Van Dyke, The Pearlies", "Mary Poppins (Original Soundtrack)"), "gradient"),
    ("he", NowPlaying(PLAYING, "שיר לשלום", "להקת הנח\"ל", "הלהקות הצבאיות"), "portrait"),
    ("he_long", NowPlaying(PLAYING, "תגידי מה את רוצה ממני (feat. עומר אדם)", "אושר כהן ונועה קירל", "סינגל"), "red"),
    ("red_cover", NowPlaying(PLAYING, "Red", "Taylor Swift", "Red (Taylor's Version)"), "red"),
    ("no_art", NowPlaying(PLAYING, "Clair de Lune", "Claude Debussy", "Suite bergamasque"), None),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cover", type=Path, help="real cover image for track screens")
    ap.add_argument("--out", type=Path, default=ROOT / "out" / "preview")
    ap.add_argument("--palette", default="auto", choices=["auto", "bw", "bwr"])
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    now = datetime(2026, 9, 25, 14, 32)
    opts = Opts(owner="Ofri")

    screens = []
    for name, np, cover in FIXTURES:
        src = Image.open(args.cover).convert("RGB") if args.cover else (synth_cover(cover) if cover else None)
        art = artmod.dither(src, args.palette) if src else None
        screens.append((name, render_track(np, PLAYING, art, opts, now)))
    screens.append(("paused", render_track(FIXTURES[0][1], PAUSED, artmod.dither(synth_cover("gradient")), opts, now)))
    screens.append(("idle", render_idle(FIXTURES[1][1], opts, now)))
    screens.append(("idle_empty", render_idle(None, opts, now)))
    screens.append(("error", render_error("Last.fm said: Invalid API key (code 10)", opts, now)))

    for name, img in screens:
        frame = pack(img)
        (args.out / f"{name}.png").write_bytes(preview_png(img, 1))
        (args.out / f"{name}@4x.png").write_bytes(preview_png(img, 4))
        print(f"{name:12s} frame {frame.id}  {len(frame.data)} B")
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
