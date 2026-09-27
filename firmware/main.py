# Now Playing e-Ink: Pico 2 W firmware.
# Polls the Home Assistant add-on for a ready-made frame and shows it. All the
# rendering happens on the add-on; this only checks the frame and streams it out.
import binascii
import gc
import struct
import time

import machine
from machine import WDT, Pin

import config
import flatyaml
import net
from canvas import Landscape
from epd2in13b import EPD, PLANE_LEN

FW = "0.1.0"
FRAME_LEN = 16 + 2 * PLANE_LEN
HEADER = "<4sBBHHHI"
LOCAL_MIN_REFRESH_MS = 60_000  # last-line protection for the panel
OFFLINE_SCREEN_AFTER_S = 600
DEFAULT_POLL_S = 15
LAST_ID_FILE = "last_id"

SECRETS = flatyaml.load(config.SECRETS_FILE)

led = Pin("LED", Pin.OUT)
wdt = WDT(timeout=8000) if config.USE_WATCHDOG else None


def feed():
    if wdt:
        wdt.feed()


def sleep_s(s):
    end = time.ticks_add(time.ticks_ms(), int(s * 1000))
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        feed()
        time.sleep_ms(250)


def blink(n):
    for _ in range(n):
        led(1)
        time.sleep_ms(120)
        led(0)
        time.sleep_ms(180)
        feed()


def load_last_id():
    try:
        with open(LAST_ID_FILE) as f:
            return f.read().strip()
    except OSError:
        return ""


def save_last_id(fid):
    with open(LAST_ID_FILE, "w") as f:
        f.write(fid)


def valid(buf, n):
    if n != FRAME_LEN:
        return False
    magic, ver, _flags, w, h, plen, crc = struct.unpack_from(HEADER, buf, 0)
    if magic != b"NPE1" or ver != 1 or w != 122 or h != 250 or plen != PLANE_LEN:
        return False
    if not hasattr(binascii, "crc32"):  # not in every MicroPython build; TCP already checksums
        return True
    return binascii.crc32(memoryview(buf)[16:FRAME_LEN]) & 0xFFFFFFFF == crc


class Display:
    def __init__(self):
        self.epd = EPD(feed=feed)
        self.last_refresh = None

    def can_refresh(self):
        return self.last_refresh is None or time.ticks_diff(time.ticks_ms(), self.last_refresh) >= LOCAL_MIN_REFRESH_MS

    def show(self, buf):
        mv = memoryview(buf)
        led(1)
        try:
            self.epd.init()
            self.epd.show(mv[16:16 + PLANE_LEN], mv[16 + PLANE_LEN:FRAME_LEN])
            self.epd.sleep()
        finally:
            led(0)
        self.last_refresh = time.ticks_ms()


def offline_screen(buf, title, detail):
    c = Landscape()
    c.black.rect(0, 0, 250, 122, 1)
    c.red.fill_rect(1, 1, 248, 18, 1)
    c.red.text("Now Playing e-Ink", 8, 6, 0)  # white text knocked out of the red bar
    c.black.text(title, 8, 40, 1)
    c.black.text(detail[:29], 8, 60, 1)
    c.black.text("Retrying...", 8, 100, 1)
    c.to_planes(buf, config.ROTATE, feed)


def main():
    buf = bytearray(FRAME_LEN)
    disp = Display()
    shown = load_last_id()
    poll_s = DEFAULT_POLL_S
    fail_since = None
    offline_shown = False
    wlan = None
    boot = time.ticks_ms()

    while True:
        feed()
        err_title = None
        try:
            if wlan is None or not wlan.isconnected():
                err_title = "Wi-Fi lost"
                wlan = net.connect(SECRETS["wifi_ssid"], SECRETS["wifi_password"], config.COUNTRY, feed)
                print("wifi", wlan.ifconfig()[0])
            err_title = "Server unreachable"
            q = "/api/v1/frame?fw=%s&up=%d&mem=%d&rssi=%d&shown=%s" % (
                FW, time.ticks_diff(time.ticks_ms(), boot) // 1000, gc.mem_free(), wlan.status("rssi"), shown)
            hdrs = {"Authorization": "Bearer " + SECRETS["device_token"]}
            if shown:
                hdrs["If-None-Match"] = '"%s"' % shown
            status, rh, n = net.get(config.SERVER_HOST, config.SERVER_PORT, q, hdrs, buf, feed)
            poll_s = int(rh.get("x-poll-seconds", DEFAULT_POLL_S))
            fail_since, offline_shown = None, False

            if status == 200:
                fid = rh.get("etag", "").strip('"')
                if not valid(buf, n):
                    print("bad frame", n)
                    blink(3)
                elif fid != shown and disp.can_refresh():
                    print("show", fid)
                    disp.show(buf)
                    shown = fid
                    save_last_id(fid)
            elif status == 401:
                print("bad token")
                blink(5)
            elif status not in (304, 503):
                print("http", status)
        except Exception as e:
            print("error:", err_title, e)
            blink(2)
            if fail_since is None:
                fail_since = time.time()
            if not offline_shown and time.time() - fail_since >= OFFLINE_SCREEN_AFTER_S and disp.can_refresh():
                detail = "%s:%d" % (config.SERVER_HOST, config.SERVER_PORT) if err_title != "Wi-Fi lost" else SECRETS["wifi_ssid"]
                offline_screen(buf, err_title or "Error", detail)
                disp.show(buf)
                shown = ""  # force a redraw once the server is back
                offline_shown = True
            gc.collect()
            sleep_s(min(60, 5 * (1 + int(time.time() - fail_since) // 60)))
            continue
        gc.collect()
        sleep_s(poll_s)


try:
    main()
except Exception as e:  # anything unexpected: log, then reboot cleanly
    print("fatal:", e)
    time.sleep(5)
    machine.reset()
