# Ofri's Now-Playing e-Ink display

A Raspberry Pi **Pico 2 W** with a **2.13" black/white/red e-paper** display that shows the cover, title and artist of whatever Ofri is playing on Spotify.

```
Spotify ─► Last.fm  or  HA Spotify integration
               │
               ▼
   Home Assistant add-on  (nowplaying_eink/)
   poll source → refresh policy → render 250×122 → dither → 8 KB frame
               │   GET :8099/api/v1/frame   (token, ETag)
               ▼
   Pico 2 W (firmware/)  → SPI → e-paper
```

Why the work is split this way: the Pico has no JPEG decoder and no Hebrew text support, so the add-on draws everything. The Pico just downloads two 4,000-byte bitplanes and sends them to the panel.

## Repo
| Path | What |
|---|---|
| `nowplaying_eink/` | Home Assistant add-on (Python 3, aiohttp, Pillow) |
| `nowplaying_eink/app/render/` | Layout, fonts/bidi, cover dithering, frame packing |
| `nowplaying_eink/app/policy.py` | When the panel may refresh (settle, 180 s gap, quiet hours, 24 h) |
| `firmware/` | MicroPython for the Pico 2 W |
| `tools/preview.py` | Render every screen to PNG, no hardware needed |
| `tools/deploy.ps1` | Copy the firmware to the Pico with `mpremote` |
| `docs/` | Wiring, Last.fm setup, Spotify/HA setup |

## Getting started
1. **Wire it.** See [docs/wiring.md](docs/wiring.md). Seven wires go to pins 11–18 on the left side; VCC goes to pin 36.
2. **Song source.** Use [Last.fm](docs/lastfm-setup.md) (no Premium needed) or the [HA Spotify integration](docs/spotify-ha-setup.md) (Premium needed).
3. **Install the add-on.**
   - In HA: Settings → Add-ons → Add-on store → ⋮ → Repositories → add this repo's URL.
   - Install **Now Playing e-Ink**, configure it, and start it.
4. **Flash the Pico.**
   - Install MicroPython for `RPI_PICO2_W` from https://micropython.org/download/RPI_PICO2_W/.
   - `pip install mpremote`.
   - Copy `secrets.example.yaml` to `secrets.yaml` (git-ignored) and fill in Wi-Fi and `device_token`. Non-secret settings (server IP, rotation) are in `firmware/config.py`.
5. **Calibrate once.**
   - Set `USE_WATCHDOG = False`, then run `mpremote run firmware/testpattern.py`.
   - If the image is in the wrong corner or mirrored, change `ROTATE` and the add-on's `rotate`.
   - If red and white are swapped, flip `RED_INVERT` in `firmware/lib/epd2in13b.py`.
6. **Deploy.** Set `USE_WATCHDOG = True`, then run `.\tools\deploy.ps1`.

## Develop without hardware
```powershell
pip install aiohttp pillow python-bidi pytest
cd nowplaying_eink; python -m pytest -q tests; cd ..
python tools/preview.py            # → out/preview/*.png
python tools/preview.py --cover some.jpg
```
To run the add-on locally against your real Home Assistant, put a long-lived access token in `secrets.yaml` (`ha_token`), check `ha_url` in `nowplaying_eink/dev_options.json`, then:
```powershell
cd nowplaying_eink; python -m app.main --options dev_options.json --secrets ../secrets.yaml
```

## Screen
```
┌────────────┬──────────────────────────┐
│            │ ▶ NOW PLAYING            │  red label
│   cover    │ Title (bold, ≤2 lines)   │  black
│  122×122   │ Artist (≤2 lines)        │  red
│  dithered  │ Album                    │  black
│            │ ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄ │
│            │ ♪ Ofri              14:32│  time of last refresh
└────────────┴──────────────────────────┘
```
- Hebrew titles and artists display right to left and are right-aligned.
- Covers use red ink only when they are clearly red (`art_palette: auto`).
- There's also a paused label (HA source only), an idle screen, and an error screen.
