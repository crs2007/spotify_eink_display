"""Landscape 'P' canvas → panel-native bitplanes + NPE1 header.

Frame layout (little endian), 8016 bytes total:
    0  4  magic b"NPE1"
    4  1  version (1)
    5  1  flags   bit0 = has red
    6  2  native width  (122)
    8  2  native height (250)
   10  2  plane length  (4000 = 16 bytes/row × 250 rows)
   12  4  crc32 of both planes
   16  …  black plane: 1 = white/red(no black ink), 0 = black; MSB = leftmost pixel
 4016  …  red plane:   1 = red, 0 = no red
"""
from __future__ import annotations

import hashlib
import io
import struct
import zlib
from dataclasses import dataclass

from PIL import Image

from .palette import BLACK, PREVIEW_RGB, RED

MAGIC = b"NPE1"
VERSION = 1
HEADER = struct.Struct("<4sBBHHHI")  # 16 bytes
NATIVE_W, NATIVE_H = 122, 250
ROW_BYTES = (NATIVE_W + 7) // 8
PLANE_LEN = ROW_BYTES * NATIVE_H
FRAME_LEN = HEADER.size + 2 * PLANE_LEN


@dataclass(frozen=True)
class Frame:
    id: str
    data: bytes
    image: Image.Image  # landscape 'P' image, for previews


def to_native(img: Image.Image, rotate: int) -> Image.Image:
    """250×122 landscape → 122×250 portrait (panel RAM order)."""
    t = Image.Transpose.ROTATE_90 if rotate == 90 else Image.Transpose.ROTATE_270
    return img.transpose(t)


def _plane(native: Image.Image, on) -> bytes:
    """Pixels where on(ink) is True become bit 1. PIL '1' packs MSB-first, rows byte-padded."""
    if native.mode != "P":
        raise ValueError("expected 'P' image")
    idx = Image.frombytes("L", native.size, native.tobytes())  # raw ink indices, no palette
    return idx.point([255 if on(i) else 0 for i in range(256)], mode="1").tobytes()


def pack(img: Image.Image, rotate: int = 90) -> Frame:
    if img.size != (NATIVE_H, NATIVE_W):
        raise ValueError(f"expected 250×122 canvas, got {img.size}")
    native = to_native(img, rotate)
    black = _plane(native, lambda i: i != BLACK)
    red = _plane(native, lambda i: i == RED)
    assert len(black) == len(red) == PLANE_LEN
    planes = black + red
    has_red = any(red)
    header = HEADER.pack(MAGIC, VERSION, 1 if has_red else 0, NATIVE_W, NATIVE_H, PLANE_LEN, zlib.crc32(planes))
    fid = hashlib.sha1(planes).hexdigest()[:16]
    return Frame(fid, header + planes, img)


def preview_png(img: Image.Image, scale: int = 1) -> bytes:
    rgb = Image.new("RGB", img.size)
    lut = {k: v for k, v in PREVIEW_RGB.items()}
    rgb.putdata([lut.get(p, (255, 0, 255)) for p in img.getdata()])
    if scale > 1:
        rgb = rgb.resize((img.width * scale, img.height * scale), Image.NEAREST)
    buf = io.BytesIO()
    rgb.save(buf, "PNG")
    return buf.getvalue()
