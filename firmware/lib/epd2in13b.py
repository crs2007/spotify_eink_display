# Minimal driver for the Waveshare 2.13" e-Paper (B) V4, 250x122 B/W/R (SSD1680).
# Trimmed port of Waveshare's Pico_ePaper-2.13-B_V4.py: no framebuffer, it only
# streams two ready-made native planes (122x250, 16 bytes/row) to the panel.
from machine import Pin, SPI
import time

WIDTH = 122  # native (portrait) width in pixels
HEIGHT = 250
ROW_BYTES = 16
PLANE_LEN = ROW_BYTES * HEIGHT  # 4000

# Frame red plane uses 1 = red. Waveshare's V4 init sets 0x21 = 0x80 (inverse red
# RAM), so the bits are inverted on the way out. If red and white come out
# swapped when you run testpattern.py, flip this.
RED_INVERT = True

BUSY_TIMEOUT_MS = 30000


class EPD:
    def __init__(self, spi_id=1, sck=10, mosi=11, cs=9, dc=8, rst=12, busy=13, feed=None):
        self.spi = SPI(spi_id, baudrate=4_000_000, polarity=0, phase=0, sck=Pin(sck), mosi=Pin(mosi))
        self.cs = Pin(cs, Pin.OUT, value=1)
        self.dc = Pin(dc, Pin.OUT, value=0)
        self.rst = Pin(rst, Pin.OUT, value=1)
        self.busy = Pin(busy, Pin.IN, Pin.PULL_UP)
        self.feed = feed or (lambda: None)  # watchdog feeder
        self._scratch = bytearray(250)

    # -- low level ------------------------------------------------------------
    def _cmd(self, c):
        self.dc(0)
        self.cs(0)
        self.spi.write(bytes((c,)))
        self.cs(1)

    def _data(self, buf):
        self.dc(1)
        self.cs(0)
        self.spi.write(buf)
        self.cs(1)

    def _data_inverted(self, mv):
        s = self._scratch
        n = len(s)
        self.dc(1)
        self.cs(0)
        for off in range(0, len(mv), n):
            chunk = mv[off:off + n]
            for i in range(len(chunk)):
                s[i] = chunk[i] ^ 0xFF
            self.spi.write(memoryview(s)[:len(chunk)])
        self.cs(1)

    def wait_busy(self):
        """SSD1680 holds BUSY high while working. Feeds the watchdog meanwhile."""
        t0 = time.ticks_ms()
        while self.busy.value() == 1:
            self.feed()
            if time.ticks_diff(time.ticks_ms(), t0) > BUSY_TIMEOUT_MS:
                raise OSError("EPD busy timeout")
            time.sleep_ms(20)

    def reset(self):
        self.rst(1)
        time.sleep_ms(50)
        self.rst(0)
        time.sleep_ms(2)
        self.rst(1)
        time.sleep_ms(50)

    # -- panel ops ------------------------------------------------------------
    def init(self):
        self.reset()
        self.wait_busy()
        self._cmd(0x12)  # SW reset
        self.wait_busy()
        self._cmd(0x01)  # driver output control: 250 gates
        self._data(b"\xf9\x00\x00")
        self._cmd(0x11)  # data entry: X+, Y+
        self._data(b"\x03")
        self._cmd(0x44)  # RAM X window: 0..15 (bytes)
        self._data(bytes((0, (WIDTH - 1) >> 3)))
        self._cmd(0x45)  # RAM Y window: 0..249
        self._data(bytes((0, 0, (HEIGHT - 1) & 0xFF, (HEIGHT - 1) >> 8)))
        self._cmd(0x3C)  # border waveform
        self._data(b"\x05")
        self._cmd(0x18)  # internal temperature sensor
        self._data(b"\x80")
        self._cmd(0x21)  # display update control (inverse red RAM)
        self._data(b"\x80\x80")
        self._cursor()
        self.wait_busy()

    def _cursor(self):
        self._cmd(0x4E)
        self._data(b"\x00")
        self._cmd(0x4F)
        self._data(b"\x00\x00")

    def show(self, black, red):
        """black: 4000 B (1=white). red: 4000 B (1=red). Takes ~15 s (full refresh)."""
        self._cursor()
        self._cmd(0x24)
        self._data(black)
        self._cursor()
        self._cmd(0x26)
        if RED_INVERT:
            self._data_inverted(red)
        else:
            self._data(red)
        self._cmd(0x20)  # master activation
        self.wait_busy()

    def sleep(self):
        self._cmd(0x10)  # deep sleep mode 1 (RAM retained not needed)
        self._data(b"\x01")
        time.sleep_ms(100)
