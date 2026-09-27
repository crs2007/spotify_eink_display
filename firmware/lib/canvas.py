# Local drawing for the rare screens the Pico makes itself (offline error,
# calibration). Draws landscape 250x122 and rotates into native planes exactly
# like the add-on's pack.py (rotate=90: counter-clockwise; 270: clockwise).
import framebuf

LW, LH = 250, 122
NW, NH, ROW = 122, 250, 16


class Landscape:
    def __init__(self):
        stride = (LW + 7) // 8
        self._kb = bytearray(stride * LH)
        self._rb = bytearray(stride * LH)
        self.black = framebuf.FrameBuffer(self._kb, LW, LH, framebuf.MONO_HLSB)  # 1 = black ink
        self.red = framebuf.FrameBuffer(self._rb, LW, LH, framebuf.MONO_HLSB)  # 1 = red ink

    def to_planes(self, out, rotate=90, feed=lambda: None):
        """Write black plane (1=white) at out[16:4016] and red plane (1=red) at out[4016:8016]."""
        kp = memoryview(out)[16:16 + ROW * NH]
        rp = memoryview(out)[16 + ROW * NH:16 + 2 * ROW * NH]
        for i in range(len(kp)):
            kp[i] = 0xFF
            rp[i] = 0x00
        kpx, rpx = self.black.pixel, self.red.pixel
        for y in range(LH):
            feed()  # ~30k pixels: keep the watchdog happy
            for x in range(LW):
                if rotate == 90:
                    nx, ny = y, LW - 1 - x
                else:
                    nx, ny = LH - 1 - y, x
                idx = ny * ROW + (nx >> 3)
                bit = 0x80 >> (nx & 7)
                if rpx(x, y):
                    rp[idx] |= bit
                elif kpx(x, y):
                    kp[idx] &= ~bit & 0xFF
