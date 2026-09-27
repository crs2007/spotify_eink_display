# Wiring: 2.13" e-Paper (B) 8-pin cable → Pico 2 W

Visual version: [wiring.drawio](wiring.drawio). Open it at https://app.diagrams.net (File → Open from → Device) or in draw.io Desktop.

The wire colours below are Waveshare's standard cable colours. **Go by the labels printed on the display board, not by colour.** Clone cables use other colours.

| # | Panel pin | Waveshare wire | → Pico 2 W | Physical pin |
|---|---|---|---|---|
| 1 | VCC  | grey   | 3V3(OUT)        | **36** |
| 2 | GND  | brown  | GND             | **18** (any GND works) |
| 3 | DIN  | blue   | GP11 (SPI1 TX)  | **15** |
| 4 | CLK  | yellow | GP10 (SPI1 SCK) | **14** |
| 5 | CS   | orange | GP9             | **12** |
| 6 | DC   | green  | GP8             | **11** |
| 7 | RST  | white  | GP12            | **16** |
| 8 | BUSY | purple | GP13            | **17** |

```
                                ┌──────[ USB ]──────┐
                        GP0   1 │●                 ●│ 40  VBUS
                        GP1   2 │●                 ●│ 39  VSYS
                        GND   3 │●                 ●│ 38  GND
                        GP2   4 │●                 ●│ 37  3V3_EN
                        GP3   5 │●                 ●│ 36  3V3(OUT) ◄── VCC (grey)
                        GP4   6 │●                 ●│ 35  ADC_VREF
                        GP5   7 │●                 ●│ 34  GP28
                        GND   8 │●                 ●│ 33  GND
                        GP6   9 │●                 ●│ 32  GP27
                        GP7  10 │●    PICO 2 W     ●│ 31  GP26
 DC   (green)  ──►      GP8  11 │●   (top view,    ●│ 30  RUN
 CS   (orange) ──►      GP9  12 │●    USB up)      ●│ 29  GP22
                        GND  13 │●                 ●│ 28  GND
 CLK  (yellow) ──►      GP10 14 │●                 ●│ 27  GP21
 DIN  (blue)   ──►      GP11 15 │●                 ●│ 26  GP20
 RST  (white)  ──►      GP12 16 │●                 ●│ 25  GP19
 BUSY (purple) ──►      GP13 17 │●                 ●│ 24  GP18
 GND  (brown)  ──►      GND  18 │●                 ●│ 23  GND
                        GP14 19 │●                 ●│ 22  GP17
                        GP15 20 │●                 ●│ 21  GP16
                                └───────────────────┘
```

- 7 of the 8 wires go to one row of pins on the **left side, pins 11–18**. Only VCC goes to the right side (pin 36).
- Use **3V3(OUT)**, not VBUS or VSYS.
- Check VCC and GND twice before you plug in USB.
- If your board has a switch labelled "Interface config" / BS, set it to **4-line SPI (0)**.
- If you use a different GPIO, change the pin numbers in `EPD(...)` in `firmware/lib/epd2in13b.py`.

## Check the panel version
The sticker or the flex cable should say **2.13inch e-Paper (B) V4**. The driver is written for V4 (SSD1680). If yours says V3 (or it's another brand), say so, because the setup sequence in the driver is different.
