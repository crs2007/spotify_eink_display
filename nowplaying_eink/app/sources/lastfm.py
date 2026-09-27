"""Last.fm source: works without Spotify Premium (Ofri links Spotify → Last.fm once)."""
from __future__ import annotations

import asyncio

import aiohttp

from ..model import IDLE, PLAYING, NowPlaying
from .base import SourceError

API = "https://ws.audioscrobbler.com/2.0/"
PLACEHOLDER = "2a96cbd8b46e442fc41c2b86b821562f"  # Last.fm's grey star "no image"
_SIZE_ORDER = ("extralarge", "large", "medium", "small", "mega")


def _art(images) -> str | None:
    by_size = {i.get("size"): i.get("#text", "") for i in images or []}
    for size in _SIZE_ORDER:
        url = by_size.get(size) or ""
        if url and PLACEHOLDER not in url:
            return url
    return None


def parse(data: dict) -> NowPlaying:
    if "error" in data:
        raise SourceError(f"Last.fm said: {data.get('message', 'error')} (code {data['error']})")
    tracks = (data.get("recenttracks") or {}).get("track") or []
    if isinstance(tracks, dict):  # a single track comes back as an object
        tracks = [tracks]
    if not tracks:
        return NowPlaying(IDLE, source="lastfm")
    t = tracks[0]
    playing = (t.get("@attr") or {}).get("nowplaying") == "true"
    artist = t.get("artist") or {}
    return NowPlaying(
        state=PLAYING if playing else IDLE,
        title=t.get("name", ""),
        artist=artist.get("#text") or artist.get("name", ""),
        album=(t.get("album") or {}).get("#text", ""),
        art_url=_art(t.get("image")),
        source="lastfm",
    )


class LastFmSource:
    name = "Last.fm"

    def __init__(self, user: str, api_key: str):
        self.params = {
            "method": "user.getrecenttracks",
            "user": user,
            "api_key": api_key,
            "format": "json",
            "limit": "1",
        }

    async def fetch(self, session: aiohttp.ClientSession) -> NowPlaying:
        try:
            async with session.get(API, params=self.params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status >= 500:
                    raise SourceError(f"Last.fm is down (HTTP {r.status})")
                data = await r.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            raise SourceError(f"Can't reach Last.fm ({type(e).__name__})") from e
        return parse(data)
