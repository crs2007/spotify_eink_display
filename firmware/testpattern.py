# Calibration screen. Run once with the display wired:  mpremote run firmware/testpattern.py
# (Set USE_WATCHDOG = False in config.py first, or main.py's watchdog resets the board.)
# Expected (with the cable coming out as you like it):
#   * "TOP LEFT" and the arrow in the top-left corner, readable left-to-right
#   * the "BLACK" box black, the "RED" box red, the rest white
# Wrong corner / mirrored text → change ROTATE in config.py AND `rotate` in the add-on.
# Red and white swapped → flip RED_INVERT in lib/epd2in13b.py.
import sys

sys.path.append("/lib")
import config
from canvas import Landscape
from epd2in13b import EPD, PLANE_LEN

buf = bytearray(16 + 2 * PLANE_LEN)
c = Landscape()
k, r = c.black, c.red
k.rect(0, 0, 250, 122, 1)
for i in range(12):  # arrow pointing at the top-left corner
    k.hline(2, 2 + i, 12 - i, 1)
    k.vline(2 + i, 2, 12 - i, 1)
k.text("TOP LEFT", 18, 4, 1)
k.fill_rect(10, 40, 100, 40, 1)
k.text("BLACK", 40, 56, 0)
r.fill_rect(140, 40, 100, 40, 1)
r.text("RED", 178, 56, 0)  # white text knocked out of the red box
for y in range(96, 120, 4):  # checker strip: fine detail check
    for x in range(10, 240, 4):
        (k if (x + y) % 8 == 0 else r).fill_rect(x, y, 2, 2, 1)
c.to_planes(buf, config.ROTATE)

epd = EPD()
epd.init()
mv = memoryview(buf)
epd.show(mv[16:16 + PLANE_LEN], mv[16 + PLANE_LEN:])
epd.sleep()
print("done: check orientation and colours")
