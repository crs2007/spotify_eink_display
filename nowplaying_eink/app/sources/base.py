from __future__ import annotations

from typing import Protocol

from ..model import NowPlaying


class SourceError(Exception):
    """A readable reason the source couldn't be read (shown on the error screen)."""


class Source(Protocol):
    name: str

    async def fetch(self, session) -> NowPlaying:  # raises SourceError
        ...
