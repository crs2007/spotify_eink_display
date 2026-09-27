# Song source B: Home Assistant Spotify integration (needs Premium)

Since March 2026, Spotify developer apps in Development Mode:
- work only while the **app owner has Spotify Premium**, and
- allow up to **5 users**, each added by email in the app's *User Management*.

Easiest path: **Ofri** creates the app with Ofri's own (Premium) account.

1. Go to https://developer.spotify.com/dashboard → **Create app**.
   - Redirect URI: `https://my.home-assistant.io/redirect/oauth`
   - API: **Web API**.
2. Copy the **Client ID** and **Client secret**.
3. In Home Assistant: **Settings → Devices & services → Add integration → Spotify**. Enter the credentials when asked (they're stored as *Application Credentials*). Log in as Ofri.
4. Note the entity it creates, e.g. `media_player.spotify_ofri_rimer`. Its attributes should show `media_title`, `media_artist` and `entity_picture` while music plays.
5. In the add-on configuration:
   ```yaml
   source: ha_entity
   entity_id: media_player.spotify_ofri_rimer   # not media_player.office_sharon_rimer
   ```

With this source the PAUSED screen works, and it updates faster than Last.fm.

`ha_entity` works with **any** `media_player`, for example a Google Cast speaker or a Sonos that Ofri plays Spotify on. It can be useful even without Premium.
