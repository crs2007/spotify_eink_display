import zlib

from app.render.layout import new_canvas
from app.render.pack import FRAME_LEN, HEADER, PLANE_LEN, ROW_BYTES, pack
from app.render.palette import BLACK, RED


def planes(frame):
    d = frame.data
    return d[16:16 + PLANE_LEN], d[16 + PLANE_LEN:]


def bit(plane, x, y):
    return (plane[y * ROW_BYTES + x // 8] >> (7 - x % 8)) & 1


def test_header_and_length():
    f = pack(new_canvas())
    assert len(f.data) == FRAME_LEN == 8016
    magic, ver, flags, w, h, plen, crc = HEADER.unpack(f.data[:16])
    assert (magic, ver, flags, w, h, plen) == (b"NPE1", 1, 0, 122, 250, 4000)
    assert crc == zlib.crc32(f.data[16:])


def test_white_canvas_planes():
    black, red = planes(pack(new_canvas()))
    assert all(bit(black, x, y) == 1 for y in (0, 249) for x in (0, 121))
    assert not any(red)


def test_rotation_90_maps_top_right_to_native_origin():
    img = new_canvas()
    img.putpixel((249, 0), BLACK)  # landscape top-right
    img.putpixel((0, 0), RED)  # landscape top-left
    f = pack(img, rotate=90)
    black, red = planes(f)
    assert bit(black, 0, 0) == 0  # CCW: top-right → native (0, 0)
    assert bit(red, 0, 249) == 1  # top-left → native (0, 249)
    assert f.data[5] & 1  # has_red flag


def test_rotation_270():
    img = new_canvas()
    img.putpixel((0, 0), BLACK)
    black, _ = planes(pack(img, rotate=270))
    assert bit(black, 121, 0) == 0  # CW: top-left → native (121, 0)


def test_red_pixel_is_not_black_ink():
    img = new_canvas()
    img.putpixel((10, 10), RED)
    black, red = planes(pack(img))
    assert sum(bin(b).count("1") for b in red) == 1
    zeros_in_visible = sum(1 for y in range(250) for x in range(122) if bit(black, x, y) == 0)
    assert zeros_in_visible == 0


def test_id_changes_with_content():
    a = pack(new_canvas()).id
    img = new_canvas()
    img.putpixel((5, 5), BLACK)
    assert pack(img).id != a
