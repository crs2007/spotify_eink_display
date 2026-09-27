"""Add-on entry point: poll the source, apply the refresh policy, serve frames.

    python -m app.main --options /data/options.json
"""
from __future__ import annotations

import argparse
import asyncio
import hmac
import logging
import time
from datetime import datetime
from pathlib import Path

import aiohttp
from aiohttp import web

from . import config
from .model import ERROR, IDLE, Screen
from .policy import Policy, PolicyConfig, parse_quiet_hours
from .render import art as artmod
from .render.layout import Opts, render_error, render_idle, render_track
from .render.pack import Frame, pack, preview_png
from .sources.base import SourceError
from .sources.ha_entity import HaEntitySource
from .sources.lastfm import LastFmSource

log = logging.getLogger("nowplaying")
WEB_DIR = Path(__file__).resolve().parent / "web"


class Service:
    def __init__(self, s: config.Settings):
        self.s = s
        self.policy = Policy(PolicyConfig(
            min_refresh_s=s.min_refresh_s,
            settle_s=s.settle_s,
            pause_grace_s=s.pause_grace_s,
            idle_after_s=s.idle_after_min * 60,
            error_after_s=s.error_after_s,
            force_after_s=s.force_after_h * 3600,
            quiet=parse_quiet_hours(s.quiet_hours),
        ))
        self.opts = Opts(owner=s.owner_name, clean_titles=s.clean_titles)
        self.frame: Frame | None = None
        self.published_log: list[dict] = []  # last 50 publishes
        self.source_ok: bool | None = None
        self.source_msg = ""
        self.last_obs: dict = {}
        self.device: dict = {}
        self.session: aiohttp.ClientSession | None = None
        if s.source == "lastfm":
            self.source = LastFmSource(s.lastfm_user, s.lastfm_api_key)
        else:
            self.source = HaEntitySource(s.entity_id, s.ha_url, s.ha_token)

    # -- rendering -----------------------------------------------------------
    async def render(self, screen: Screen) -> Frame:
        now = datetime.now()
        if screen.kind == ERROR:
            img = render_error(screen.message, self.opts, now)
        elif screen.kind == IDLE:
            img = render_idle(screen.track, self.opts, now)
        else:
            t = screen.track
            cover = None
            if t.art_url and self.session is not None:
                raw = await artmod.fetch(self.session, t.art_url, self.s.art_dir, t.art_headers)
                if raw is not None:
                    cover = await asyncio.to_thread(artmod.dither, raw, self.s.art_palette)
            img = render_track(t, screen.kind, cover, self.opts, now)
        return pack(img, self.s.rotate)

    # -- loop ----------------------------------------------------------------
    async def tick(self) -> None:
        now = time.time()
        try:
            np = await self.source.fetch(self.session)
            if not self.source_ok:
                log.info("source %s OK", self.source.name)
            self.source_ok, self.source_msg = True, ""
            obs = {"state": np.state, "title": np.title, "artist": np.artist, "album": np.album}
            if obs != self.last_obs:
                log.info("source: %s — %s — %s [%s]", np.artist, np.title, np.album, np.state)
                self.last_obs = obs
            self.policy.observe(now, np)
        except SourceError as e:
            if self.source_ok is not False or str(e) != self.source_msg:
                log.warning("source error: %s", e)
            self.source_ok, self.source_msg = False, str(e)
            self.policy.observe(now, None, error=str(e))

        screen = self.policy.decide(now, datetime.now())
        if screen is not None:
            frame = await self.render(screen)
            self.frame = frame
            entry = {"at": datetime.now().isoformat(timespec="seconds"), "id": frame.id, "key": screen.content_key}
            self.published_log = (self.published_log + [entry])[-50:]
            log.info("publish %s  %s", frame.id, screen.content_key)

    async def run(self) -> None:
        while True:
            try:
                await self.tick()
            except Exception:  # keep serving the last frame no matter what
                log.exception("tick failed")
            await asyncio.sleep(self.s.source_poll_s)

    # -- http ----------------------------------------------------------------
    def _authorized(self, req: web.Request) -> bool:
        auth = req.headers.get("Authorization", "")
        token = auth[7:] if auth.startswith("Bearer ") else req.query.get("token", "")
        return hmac.compare_digest(token.encode(), self.s.device_token.encode())

    async def h_frame(self, req: web.Request) -> web.Response:
        if not self._authorized(req):
            return web.Response(status=401, text="bad token")
        q = req.query
        self.device = {
            "ip": req.remote,
            "seen": datetime.now().isoformat(timespec="seconds"),
            **{k: q[k] for k in ("rssi", "up", "mem", "fw", "shown") if k in q},
        }
        headers = {"X-Poll-Seconds": str(self.s.poll_s), "Cache-Control": "no-store"}
        if self.frame is None:
            return web.Response(status=503, text="no frame yet", headers=headers)
        etag = f'"{self.frame.id}"'
        headers["ETag"] = etag
        if req.headers.get("If-None-Match") == etag:
            return web.Response(status=304, headers=headers)
        return web.Response(body=self.frame.data, content_type="application/octet-stream", headers=headers)

    async def h_state(self, req: web.Request) -> web.Response:
        p = self.policy
        nxt = p.next_allowed_at()
        return web.json_response({
            "source": {"name": self.source.name, "ok": self.source_ok, "message": self.source_msg, "last": self.last_obs},
            "candidate": p.candidate.content_key if p.candidate else None,
            "published": p.published.content_key if p.published else None,
            "frame_id": self.frame.id if self.frame else None,
            "next_refresh_allowed": datetime.fromtimestamp(nxt).isoformat(timespec="seconds") if nxt else None,
            "device": self.device,
            "history": self.published_log,
        })

    async def h_preview(self, req: web.Request) -> web.Response:
        scale = max(1, min(8, int(req.query.get("scale", "3"))))
        if req.query.get("candidate") and self.policy.candidate is not None:
            img = (await self.render(self.policy.candidate)).image
        elif self.frame is not None:
            img = self.frame.image
        else:
            return web.Response(status=404, text="no frame yet")
        return web.Response(body=preview_png(img, scale), content_type="image/png", headers={"Cache-Control": "no-store"})

    async def h_force(self, req: web.Request) -> web.Response:
        if not self._authorized(req):
            return web.Response(status=401, text="bad token")
        self.policy.force_next()
        await self.tick()
        return web.json_response({"frame_id": self.frame.id if self.frame else None})

    async def h_index(self, req: web.Request) -> web.FileResponse:
        return web.FileResponse(WEB_DIR / "index.html")

    def app(self) -> web.Application:
        a = web.Application()
        a.router.add_get("/", self.h_index)
        a.router.add_get("/api/v1/frame", self.h_frame)
        a.router.add_get("/api/v1/state", self.h_state)
        a.router.add_post("/api/v1/force", self.h_force)
        a.router.add_get("/preview.png", self.h_preview)

        async def startup(_):
            self.session = aiohttp.ClientSession(
                headers={"User-Agent": "nowplaying-eink/0.1"},
                connector=aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver()),  # no aiodns quirks
            )
            a["loop_task"] = asyncio.create_task(self.run())

        async def cleanup(_):
            a["loop_task"].cancel()
            await self.session.close()

        a.on_startup.append(startup)
        a.on_cleanup.append(cleanup)
        return a


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--options", default="/data/options.json")
    ap.add_argument("--secrets", help="flat secrets.yaml filling empty secret options (local dev)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    s = config.load(args.options, args.secrets)
    svc = Service(s)
    log.info("source=%s owner=%s min_refresh=%ss port=%s", s.source, s.owner_name, s.min_refresh_s, s.port)
    web.run_app(svc.app(), host=s.host, port=s.port, print=None, access_log=None)


if __name__ == "__main__":
    main()
