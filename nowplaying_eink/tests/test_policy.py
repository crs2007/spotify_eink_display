from datetime import datetime, time as dtime

from app.model import IDLE, PAUSED, PLAYING, NowPlaying
from app.policy import Policy, PolicyConfig, in_quiet, parse_quiet_hours

NOON = datetime(2026, 9, 25, 12, 0)


def song(n, state=PLAYING):
    return NowPlaying(state, f"Song {n}", "Artist", "Album")


def run(p, t0, t1, np, step=5, error=None):
    """Observe np every `step` s from t0 to t1; return [(t, content_key)] published."""
    out = []
    t = t0
    while t <= t1:
        p.observe(t, np, error=error)
        s = p.decide(t, NOON)
        if s:
            out.append((t, s.content_key))
        t += step
    return out


def test_first_frame_is_immediate():
    p = Policy(PolicyConfig())
    assert run(p, 0, 0, song(1)) == [(0, "playing:artist|song 1|album")]


def test_skip_storm_gives_one_refresh_with_last_song():
    p = Policy(PolicyConfig())
    run(p, 0, 0, song(0))
    pubs = []
    for i, t0 in enumerate(range(200, 250, 10)):  # skipping every 10 s
        pubs += run(p, t0, t0 + 9, song(i + 1))
    pubs += run(p, 250, 400, song(5))
    assert len(pubs) == 1
    assert pubs[0][1].endswith("song 5|album")
    assert pubs[0][0] >= 240 + 20  # settled on song 5 first


def test_min_refresh_interval():
    p = Policy(PolicyConfig())
    run(p, 0, 0, song(1))
    assert run(p, 5, 175, song(2)) == []  # held back by the 180 s gate
    assert [t for t, _ in run(p, 180, 200, song(2))] == [180]


def test_pause_grace_then_paused():
    p = Policy(PolicyConfig())
    run(p, 0, 0, song(1))
    pubs = run(p, 5, 600, song(1, PAUSED))
    assert len(pubs) == 1 and pubs[0][1].startswith("paused:")
    assert pubs[0][0] >= 5 + 120


def test_short_pause_does_not_refresh():
    p = Policy(PolicyConfig())
    run(p, 0, 0, song(1))
    assert run(p, 5, 60, song(1, PAUSED)) + run(p, 65, 600, song(1)) == []


def test_idle_after_timeout_keeps_last_track():
    p = Policy(PolicyConfig())
    run(p, 0, 0, song(1))
    idle = NowPlaying(IDLE, "Song 1", "Artist", "Album")
    pubs = run(p, 5, 15 * 60 + 60, idle)
    assert len(pubs) == 1 and pubs[0][1] == "idle"
    assert pubs[0][0] >= 15 * 60
    assert p.published.track.title == "Song 1"


def test_transient_error_ignored_long_error_shown():
    p = Policy(PolicyConfig())
    run(p, 0, 0, song(1))
    assert run(p, 5, 200, None, error="boom") == []
    pubs = run(p, 205, 600, None, error="boom")
    assert len(pubs) == 1 and pubs[0][1] == "error:boom"
    assert pubs[0][0] >= 5 + 300


def test_forced_refresh_after_23h_even_if_unchanged():
    p = Policy(PolicyConfig())
    run(p, 0, 0, song(1))
    pubs = run(p, 60, 23 * 3600 + 60, song(1), step=60)
    assert [t for t, _ in pubs] == [23 * 3600]


def test_quiet_hours_block_changes():
    p = Policy(PolicyConfig(quiet=parse_quiet_hours("00:30-07:00")))
    p.observe(0, song(1))
    p.decide(0, NOON)
    night = datetime(2026, 9, 25, 3, 0)
    for t in range(5, 1000, 5):
        p.observe(t, song(2))
        assert p.decide(t, night) is None
    assert p.decide(1000, NOON) is not None


def test_quiet_window_wraps_midnight():
    w = (dtime(23, 0), dtime(6, 0))
    assert in_quiet(datetime(2026, 1, 1, 23, 30), w)
    assert in_quiet(datetime(2026, 1, 1, 5, 59), w)
    assert not in_quiet(datetime(2026, 1, 1, 6, 0), w)
    assert not in_quiet(datetime(2026, 1, 1, 12, 0), None)


def test_force_next():
    p = Policy(PolicyConfig())
    run(p, 0, 0, song(1))
    p.observe(10, song(2))
    p.force_next()
    assert p.decide(10, NOON) is not None
