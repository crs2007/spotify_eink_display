import json
from pathlib import Path

import pytest

from app.model import IDLE, PAUSED, PLAYING
from app.sources import ha_entity, lastfm
from app.sources.base import SourceError

FIX = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def test_lastfm_nowplaying():
    np = lastfm.parse(load("lastfm_nowplaying.json"))
    assert np.state == PLAYING
    assert (np.title, np.artist, np.album) == ("Blinding Lights", "The Weeknd", "After Hours")
    assert np.art_url.endswith("/300x300/abc.jpg")


def test_lastfm_not_playing_placeholder_art():
    np = lastfm.parse(load("lastfm_recent.json"))
    assert np.state == IDLE and np.title == "Old Song"
    assert np.art_url is None


def test_lastfm_error():
    with pytest.raises(SourceError, match="Invalid API key"):
        lastfm.parse({"error": 10, "message": "Invalid API key"})


def test_lastfm_empty():
    assert lastfm.parse({"recenttracks": {"track": []}}).state == IDLE


def test_ha_playing_relative_picture():
    np = ha_entity.parse(load("ha_playing.json"), "http://supervisor/core", {"Authorization": "Bearer x"})
    assert np.state == PLAYING and np.artist == "Queen"
    assert np.art_url.startswith("http://supervisor/core/api/media_player_proxy/")
    assert np.art_headers["Authorization"] == "Bearer x"


def test_ha_paused_and_idle():
    d = load("ha_playing.json")
    d["state"] = "paused"
    assert ha_entity.parse(d, "b", {}).state == PAUSED
    d["state"] = "idle"
    assert ha_entity.parse(d, "b", {}).state == IDLE


def test_ha_unavailable():
    with pytest.raises(SourceError):
        ha_entity.parse({"entity_id": "media_player.x", "state": "unavailable", "attributes": {}}, "b", {})
