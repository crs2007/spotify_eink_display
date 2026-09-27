# Wi-Fi + a tiny HTTP/1.0 GET that reads the body straight into a caller buffer.
import network
import socket
import time


def connect(ssid, password, country="IL", feed=lambda: None, timeout_s=30):
    network.country(country)
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    try:
        wlan.config(pm=network.WLAN.PM_NONE)  # CYW43 power-save causes stalls
    except Exception:
        pass
    if wlan.isconnected():
        return wlan
    wlan.connect(ssid, password)
    t0 = time.time()
    while not wlan.isconnected():
        feed()
        st = wlan.status()
        if st in (network.STAT_WRONG_PASSWORD, network.STAT_NO_AP_FOUND, network.STAT_CONNECT_FAIL):
            raise OSError("wifi status %d" % st)
        if time.time() - t0 > timeout_s:
            raise OSError("wifi timeout")
        time.sleep_ms(250)
    return wlan


def get(host, port, path, headers, buf, feed=lambda: None, timeout_s=5):
    """GET into buf. Returns (status, headers_dict_lowercase, body_len)."""
    addr = socket.getaddrinfo(host, port)[0][-1]
    s = socket.socket()
    s.settimeout(timeout_s)
    try:
        s.connect(addr)
        req = "GET %s HTTP/1.0\r\nHost: %s\r\n" % (path, host)
        for k in headers:
            req += "%s: %s\r\n" % (k, headers[k])
        s.write(req.encode() + b"\r\n")

        line = s.readline()
        parts = line.split(None, 2)
        if len(parts) < 2:
            raise OSError("bad status line")
        status = int(parts[1])
        hdrs = {}
        while True:
            line = s.readline()
            if not line or line == b"\r\n":
                break
            k, _, v = line.decode().partition(":")
            hdrs[k.strip().lower()] = v.strip()

        n = 0
        if status == 200:
            want = int(hdrs.get("content-length", "0"))
            if want > len(buf):
                raise OSError("body too big: %d" % want)
            mv = memoryview(buf)
            while n < want:
                feed()
                r = s.readinto(mv[n:want])
                if not r:
                    break
                n += r
            if n != want:
                raise OSError("short body %d/%d" % (n, want))
        return status, hdrs, n
    finally:
        s.close()
