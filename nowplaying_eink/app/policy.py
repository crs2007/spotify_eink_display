"""Decides *when* the panel may change.

The tri-color panel only does ~15 s full refreshes, Waveshare asks for >=180 s
between refreshes and >=1 refresh per 24 h. This module turns a stream of source
observations into rare, meaningful publishes. It is pure: time is passed in.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time as dtime

from .model import ERROR, IDLE, PAUSED, PLAYING, NowPlaying, Screen


def parse_quiet_hours(spec: str) -> tuple[dtime, dtime] | None:
    """'00:30-07:00' → (00:30, 07:00). Empty → None."""
    spec = spec.strip()
    if not spec:
        return None
    a, b = spec.split("-")
    ha, ma = (int(x) for x in a.strip().split(":"))
    hb, mb = (int(x) for x in b.strip().split(":"))
    return dtime(ha, ma), dtime(hb, mb)


def in_quiet(now_local: datetime, window: tuple[dtime, dtime] | None) -> bool:
    if window is None:
        return False
    start, end = window
    t = now_local.time()
    if start <= end:
        return start <= t < end
    return t >= start or t < end  # wraps midnight


@dataclass
class PolicyConfig:
    min_refresh_s: float = 180
    settle_s: float = 20
    pause_grace_s: float = 120
    idle_after_s: float = 15 * 60
    error_after_s: float = 300
    force_after_s: float = 23 * 3600
    quiet: tuple[dtime, dtime] | None = None


class Policy:
    def __init__(self, cfg: PolicyConfig):
        self.cfg = cfg
        self.published: Screen | None = None
        self.published_at: float | None = None
        self.candidate: Screen | None = None
        self.candidate_since: float = 0.0
        self.last_track: NowPlaying | None = None  # last playing/paused track
        self.last_active_at: float | None = None  # last time something was PLAYING
        self.paused_since: float | None = None
        self.error_since: float | None = None
        self.error_msg: str = ""
        self._force_once = False

    # -- inputs --------------------------------------------------------------
    def force_next(self) -> None:
        self._force_once = True

    def observe(self, now: float, np: NowPlaying | None, error: str | None = None) -> None:
        """Feed one source poll result (np) or a failure (error)."""
        if error is not None:
            if self.error_since is None:
                self.error_since = now
            self.error_msg = error
        else:
            self.error_since = None
            self.error_msg = ""
            if np is not None and np.state == PLAYING and np.has_track:
                self.last_track = np
                self.last_active_at = now
                self.paused_since = None
            elif np is not None and np.state == PAUSED and np.has_track:
                if self.paused_since is None or (
                    self.last_track and self.last_track.track_key != np.track_key
                ):
                    self.paused_since = now
                self.last_track = np
            else:  # idle / nothing
                if np is not None and np.has_track and self.last_track is None:
                    self.last_track = np  # remember for the idle screen
                self.paused_since = None

        desired = self._desired(now)
        if self.candidate is None or desired.content_key != self.candidate.content_key:
            self.candidate_since = now
        self.candidate = desired

    def _desired(self, now: float) -> Screen:
        c = self.cfg
        if self.error_since is not None:
            if now - self.error_since >= c.error_after_s:
                return Screen(ERROR, message=self.error_msg)
            return self.candidate or Screen(IDLE, track=self.last_track)  # ride out blips
        t = self.last_track
        if t is None:
            return Screen(IDLE)
        if self.paused_since is not None:
            paused_for = now - self.paused_since
            if paused_for >= c.idle_after_s:
                return Screen(IDLE, track=t)
            if paused_for >= c.pause_grace_s:
                return Screen(PAUSED, track=t)
            return Screen(PLAYING, track=t)
        if t.state == PLAYING and self.last_active_at is not None:
            if now - self.last_active_at < c.idle_after_s:
                return Screen(PLAYING, track=t)
        return Screen(IDLE, track=t)

    # -- decision ------------------------------------------------------------
    def next_allowed_at(self) -> float | None:
        if self.published_at is None:
            return None
        return self.published_at + self.cfg.min_refresh_s

    def decide(self, now: float, now_local: datetime) -> Screen | None:
        """Return the Screen to publish now, or None. Marks it as published."""
        cand = self.candidate
        if cand is None:
            return None
        c = self.cfg

        if self._force_once:
            self._force_once = False
            return self._publish(now, cand)

        if self.published_at is not None and now - self.published_at >= c.force_after_s:
            return self._publish(now, cand)  # 24 h anti-burn-in; ignores quiet hours

        if self.published is not None and cand.content_key == self.published.content_key:
            return None
        if in_quiet(now_local, c.quiet):
            return None
        if self.published is None:
            return self._publish(now, cand)  # first frame after start: show asap
        if now - self.candidate_since < c.settle_s:
            return None
        if now - self.published_at < c.min_refresh_s:
            return None
        return self._publish(now, cand)

    def _publish(self, now: float, s: Screen) -> Screen:
        self.published = s
        self.published_at = now
        return s
