# Song source A: Last.fm (no Spotify Premium needed)

Spotify now requires the owner of a developer app to have Premium. Last.fm avoids that, because Spotify reports every song it plays to Last.fm.

1. **Ofri:** create a free account at https://www.last.fm/join.
2. **Ofri:** connect Spotify at https://www.last.fm/settings/applications → *Spotify scrobbling* → **Connect**.
3. Play a song and check that it shows as "Scrobbling now" on Ofri's Last.fm profile.
4. **You:** create an API key at https://www.last.fm/api/account/create. Only the application name matters; leave the callback empty. Copy the **API key** (not the secret).
5. In the add-on configuration:
   ```yaml
   source: lastfm
   lastfm_user: <Ofri's Last.fm username>
   lastfm_api_key: <API key>
   ```

Notes:
- Last.fm only knows "now playing" or "not playing". A pause shows up as "not playing", so the display goes to the idle screen after `idle_after_min`. It never shows the PAUSED label.
- Covers come from Last.fm (300 px). Some tracks have none; those show a note placeholder.
- The Last.fm profile's "Hide recent listening" setting must be **off**, or the API returns nothing.
