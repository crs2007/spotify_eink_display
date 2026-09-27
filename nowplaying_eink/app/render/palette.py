"""Ink indices used in every 'P' canvas, plus preview colours."""
WHITE = 0
BLACK = 1
RED = 2

# Approximate look of a Waveshare B/W/R panel, for PNG previews only.
PREVIEW_RGB = {WHITE: (238, 236, 228), BLACK: (24, 24, 24), RED: (186, 32, 38)}


def attach(img) -> None:
    """Give a 'P' image a palette so it can be saved/viewed directly."""
    flat = []
    for i in range(256):
        flat.extend(PREVIEW_RGB.get(i, (255, 0, 255)))
    img.putpalette(flat)
