"""Add-on options (/data/options.json) → typed Settings."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, fields
from pathlib import Path

from . import flatyaml


@dataclass
class Settings:
    source: str = "lastfm"  # lastfm | ha_entity
    lastfm_user: str = ""
    lastfm_api_key: str = ""
    entity_id: str = ""
    owner_name: str = "Ofri"
    device_token: str = ""
    min_refresh_s: int = 180
    settle_s: int = 20
    pause_grace_s: int = 120
    idle_after_min: int = 15
    error_after_s: int = 300
    force_after_h: float = 23.0
    quiet_hours: str = ""
    art_palette: str = "auto"  # auto | bw | bwr
    clean_titles: bool = True
    rotate: int = 90  # 90 | 270
    poll_s: int = 15  # how often the Pico should poll
    # Dev / outside-HA overrides (not exposed in the add-on UI)
    ha_url: str = ""  # e.g. http://homeassistant.local:8123 ; empty = Supervisor proxy
    ha_token: str = ""  # long-lived token ; empty = $SUPERVISOR_TOKEN
    data_dir: str = "/data"
    host: str = "0.0.0.0"
    port: int = 8099

    @property
    def source_poll_s(self) -> int:
        return 10 if self.source == "lastfm" else 5

    @property
    def art_dir(self) -> Path:
        return Path(self.data_dir) / "art"


SECRET_KEYS = ("device_token", "lastfm_api_key", "ha_token")


def load(path: str | os.PathLike, secrets_path: str | os.PathLike | None = None) -> Settings:
    """Options JSON; empty secret options are filled from secrets.yaml (local dev)."""
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    if secrets_path and Path(secrets_path).exists():
        sec = flatyaml.load(str(secrets_path))
        for k in SECRET_KEYS:
            if not raw.get(k) and sec.get(k):
                raw[k] = sec[k]
    known = {f.name for f in fields(Settings)}
    s = Settings(**{k: v for k, v in raw.items() if k in known})
    s.rotate = int(s.rotate)  # HA list(90|270) options arrive as strings
    validate(s)
    return s


def validate(s: Settings) -> None:
    if s.source not in ("lastfm", "ha_entity"):
        raise ValueError(f"source must be lastfm or ha_entity, got {s.source!r}")
    if s.source == "lastfm" and not (s.lastfm_user and s.lastfm_api_key):
        raise ValueError("lastfm source needs lastfm_user and lastfm_api_key")
    if s.source == "ha_entity" and not s.entity_id.startswith("media_player."):
        raise ValueError("ha_entity source needs entity_id like media_player.spotify_ofri_rimer")
    if s.art_palette not in ("auto", "bw", "bwr"):
        raise ValueError("art_palette must be auto, bw or bwr")
    if s.rotate not in (90, 270):
        raise ValueError("rotate must be 90 or 270")
    if not s.device_token or len(s.device_token) < 16:
        raise ValueError("device_token must be at least 16 characters")
