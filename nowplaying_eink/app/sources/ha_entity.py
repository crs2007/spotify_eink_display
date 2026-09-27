"""Home Assistant media_player source (HA Spotify integration, or Cast/Sonos/...)."""
from __future__ import annotations

import asyncio
import os

import aiohttp

from ..model import IDLE, PAUSED, PLAYING, NowPlaying
from .base import SourceError

SUPERVISOR = "http://supervisor/core"


def parse(data: dict, base_url: str, headers: dict) -> NowPlaying:
    state = data.get("state", "")
    a = data.get("attributes") or {}
    kind = {"playing": PLAYING, "buffering": PLAYING, "paused": PAUSED}.get(state, IDLE)
    if state == "unavailable":
        raise SourceError(f"{data.get('entity_id', 'player')} is unavailable in Home Assistant")
    pic = a.get("entity_picture")
    art_url = (base_url + pic if pic.startswith("/") else pic) if pic else None
    return NowPlaying(
        state=kind,
        title=a.get("media_title", "") or "",
        artist=a.get("media_artist", "") or a.get("media_album_artist", "") or "",
        album=a.get("media_album_name", "") or "",
        art_url=art_url,
        art_headers=headers if art_url and art_url.startswith(base_url) else {},
        source="ha",
    )


class HaEntitySource:
    name = "Home Assistant"

    def __init__(self, entity_id: str, ha_url: str = "", token: str = ""):
        self.entity_id = entity_id
        self.base = (ha_url or SUPERVISOR).rstrip("/")
        tok = token or os.environ.get("SUPERVISOR_TOKEN", "")
        if not tok:
            raise SourceError("No Home Assistant token (SUPERVISOR_TOKEN missing)")
        self.headers = {"Authorization": f"Bearer {tok}"}

    async def fetch(self, session: aiohttp.ClientSession) -> NowPlaying:
        url = f"{self.base}/api/states/{self.entity_id}"
        try:
            async with session.get(url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 404:
                    raise SourceError(f"{self.entity_id} not found in Home Assistant")
                if r.status == 401:
                    raise SourceError("Home Assistant rejected the token")
                if r.status != 200:
                    raise SourceError(f"Home Assistant HTTP {r.status}")
                data = await r.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            raise SourceError(f"Can't reach Home Assistant ({type(e).__name__})") from e
        return parse(data, self.base, self.headers)
