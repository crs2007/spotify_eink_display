# Now Playing e-Ink

Shows the song Ofri is playing (cover, title, artist, album) on a Raspberry Pi Pico 2 W with a 2.13" black/white/red e-paper display. This add-on does all the rendering. The Pico just downloads an 8 KB frame and shows it.

## Setup
1. Pick a song source:
   - [Last.fm](https://github.com/crs2007/spotify_eink_display/blob/main/docs/lastfm-setup.md): no Premium needed.
   - [HA Spotify integration](https://github.com/crs2007/spotify_eink_display/blob/main/docs/spotify-ha-setup.md): needs Premium.
2. Set `device_token` to a long random string. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(24))"`.
3. Start the add-on and open **e-Ink** in the sidebar. You'll see:
   - the frame currently on the panel,
   - the next candidate frame,
   - the source status,
   - when the Pico last checked in.
4. On the Pico, set `SERVER_HOST` to the IP address of your Home Assistant machine, `SERVER_PORT` to `8099`, and `TOKEN` to the same `device_token`.

## When does the screen change?
Tri-color e-paper takes about 15 s to refresh and flashes while it does. Waveshare also recommends at least 180 s between refreshes and at least one refresh every 24 h. So the screen changes when **all** of these hold:
- the song (or play/pause/idle state) changed and has been stable for `settle_s` (20 s),
- at least `min_refresh_s` (180 s) have passed since the last refresh,
- it's not within `quiet_hours`.

Other rules:
- A pause shorter than `pause_grace_s` doesn't change anything.
- After `idle_after_min` with nothing playing, the display shows an idle screen.
- Every 23 h the screen is refreshed even if nothing changed, to protect it against burn-in.

## Endpoints (port 8099)
| Endpoint | Purpose |
|---|---|
| `GET /api/v1/frame` | Bearer token; ETag/304. Used by the Pico |
| `GET /api/v1/state` | JSON status and publish history |
| `GET /preview.png?scale=4[&candidate=1]` | PNG of the published or candidate frame |
| `POST /api/v1/force` | Bearer token; refresh now, ignoring the timers (testing) |
