"""Core data types shared by sources, policy and renderer."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

PLAYING = "playing"
PAUSED = "paused"
IDLE = "idle"
ERROR = "error"

_WS = re.compile(r"\s+")


def _norm(s: str) -> str:
    return _WS.sub(" ", s).strip().casefold()


@dataclass(frozen=True)
class NowPlaying:
    """What a source reports. For IDLE, title/artist may hold the last played track."""

    state: str
    title: str = ""
    artist: str = ""
    album: str = ""
    art_url: str | None = None
    art_headers: dict = field(default_factory=dict, compare=False, hash=False)
    source: str = ""

    @property
    def track_key(self) -> str:
        return "|".join(_norm(x) for x in (self.artist, self.title, self.album))

    @property
    def has_track(self) -> bool:
        return bool(self.title or self.artist)


@dataclass(frozen=True)
class Screen:
    """What should be on the panel. `content_key` excludes the clock, so the
    footer time never causes a refresh on its own."""

    kind: str  # PLAYING | PAUSED | IDLE | ERROR
    track: NowPlaying | None = None
    message: str = ""

    @property
    def content_key(self) -> str:
        if self.kind in (PLAYING, PAUSED):
            return f"{self.kind}:{self.track.track_key if self.track else ''}"
        if self.kind == ERROR:
            return f"error:{self.message}"
        return "idle"
