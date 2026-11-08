"""Our Little Universe — authoritative two-player game server.

Single service for static files and WebSocket play. Install aiohttp and run:
    python server.py

Rooms are stored as JSON in DATA_DIR. Use persistent storage for production.
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aiohttp import WSMsgType, web

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "web"
PRIVATE = ROOT / "private_assets"
DATA_DIR = Path(os.getenv("DATA_DIR", str(ROOT / "data")))
SAVE_PATH = DATA_DIR / "rooms.json"
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
TICK = 1 / 20
SPEED = 3.8
START = [(-8.4, 1.35), (8.4, 1.35)]
PHONES = [(-9.9, 0.10), (9.9, 0.10)]
SWITCHES = [(-4.75, 0.70), (4.75, 0.70)]
LOG = logging.getLogger("our-little-universe")


def finite_axis(v: Any) -> float:
    if not isinstance(v, (float, int)) or isinstance(v, bool) or not math.isfinite(v):
        return 0.0
    return max(-1.0, min(1.0, float(v)))


def near(p: "Player", target: tuple[float, float], radius: float = 2.2) -> bool:
    return math.hypot(p.x - target[0], p.z - target[1]) <= radius


@dataclass
class Player:
    token: str
    x: float
    z: float
    online: bool = False
    read: bool = False
    dx: float = 0.0
    dz: float = 0.0
    socket: web.WebSocketResponse | None = field(default=None, repr=False, compare=False)

    def saved(self) -> dict[str, Any]:
        return {"token": self.token, "x": self.x, "z": self.z, "read": self.read}

    def public(self, slot: int) -> dict[str, Any]:
        return {"slot": slot, "name": "Mustafa" if slot == 0 else "Tosh Tosh",
                "x": round(self.x, 3), "z": round(self.z, 3),
                "online": self.online, "read": self.read}


@dataclass
class Room:
    code: str
    players: list[Player | None] = field(default_factory=lambda: [None, None])
    progress: int = 0
    solved: bool = False
    memories: list[str] = field(default_factory=list)
    last_activity: float = field(default_factory=time.time)

    def saved(self) -> dict[str, Any]:
        return {"players": [p.saved() if p else None for p in self.players],
                "progress": self.progress, "solved": self.solved,
                "memories": self.memories, "last_activity": self.last_activity}

    def public(self) -> dict[str, Any]:
        return {"code": self.code, "chapter": 1, "players": [p.public(i) if p else None
                for i, p in enumerate(self.players)], "progress": self.progress,
                "solved": self.solved, "memories": self.memories}


class Game:
    def __init__(self, save_path: Path = SAVE_PATH):
        self.save_path = save_path
        self.rooms: dict[str, Room] = {}
        self.changed = False
        self.running = True
        self._load()

    def _load(self) -> None:
        if not self.save_path.exists():
            return
        try:
            raw = json.loads(self.save_path.read_text(encoding="utf-8"))
            for code, entry in raw.items():
                if not (len(code) == 6 and all(c in ALPHABET for c in code)):
                    continue
                room = Room(code, progress=int(entry.get("progress", 0)),
                            solved=bool(entry.get("solved", False)),
                            memories=list(entry.get("memories", [])),
                            last_activity=float(entry.get("last_activity", time.time())))
                for i, p in enumerate(entry.get("players", [])[:2]):
                    if p and isinstance(p.get("token"), str):
                        room.players[i] = Player(token=p["token"],
                                                  x=float(p.get("x", START[i][0])),
                                                  z=float(p.get("z", START[i][1])),
                                                  read=bool(p.get("read", False)))
                self.rooms[code] = room
            LOG.info("Loaded %d saved rooms", len(self.rooms))
        except (ValueError, TypeError, KeyError, OSError) as exc:
            LOG.error("Could not load saved rooms: %s", exc)

    def save(self) -> None:
        if not self.changed:
            return
        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.save_path.with_suffix(".tmp")
        temp.write_text(json.dumps({code: room.saved() for code, room in self.rooms.items()},
                                   indent=2), encoding="utf-8")
        temp.replace(self.save_path)
        self.changed = False

    def create(self) -> tuple[Room, Player]:
        for _ in range(100):
            code = "".join(secrets.choice(ALPHABET) for _ in range(6))
            if code not in self.rooms:
                break
        else:
            raise RuntimeError("Could not generate unique room code")
        room = Room(code)
        player = Player(token=secrets.token_urlsafe(32), x=START[0][0], z=START[0][1])
        room.players[0] = player
        self.rooms[code] = room
        self.changed = True
        self.save()
        return room, player

    def join(self, code: str, token: str | None = None) -> tuple[Room, Player, int]:
        room = self.rooms.get(code.strip().upper())
        if room is None:
            raise ValueError("That room code doesn't exist. Check the invitation.")
        if token:
            for i, p in enumerate(room.players):
                if p and secrets.compare_digest(p.token, token):
                    return room, p, i
        for i, p in enumerate(room.players):
            if p is None:
                player = Player(token=secrets.token_urlsafe(32), x=START[i][0], z=START[i][1])
                room.players[i] = player
                self.changed = True
                self.save()
                return room, player, i
        raise ValueError("This world already has two players. Reconnect using the original device.")

    async def send(self, p: Player, data: dict[str, Any]) -> None:
        if p.socket and not p.socket.closed:
            try:
                await p.socket.send_json(data)
            except (ConnectionError, RuntimeError):
                pass

    async def announce(self, room: Room, message: str, event: str = "notice") -> None:
        for p in room.players:
            if p:
                await self.send(p, {"type": event, "message": message})

    async def broadcast(self, room: Room) -> None:
        packet = {"type": "state", "room": room.public()}
        for p in room.players:
            if p:
                await self.send(p, packet)

    async def interact(self, room: Room, p: Player, slot: int, target: str) -> None:
        if target == "phone":
            if not near(p, PHONES[slot]):
                await self.send(p, {"type": "notice", "message": "Walk closer to your phone first."})
                return
            p.read = True
            clue = ("My clue says: The MOON must go first. Tosh Tosh has the other half."
                    if slot == 0 else
                    "My clue says: The MOON is lavender, and the STAR is rose. Tell Mustafa!")
            await self.send(p, {"type": "clue", "message": clue})
            if all(other and other.read for other in room.players):
                await self.announce(room, "You both found your clues. Solve the switches together!", "toast")
        elif target in ("moon", "star"):
            which = 0 if target == "moon" else 1
            if slot != which:
                await self.send(p, {"type": "notice", "message": "Your partner needs to press this switch."})
                return
            if not near(p, SWITCHES[which]):
                await self.send(p, {"type": "notice", "message": "Move closer to your glowing switch."})
                return
            if not all(other and other.read for other in room.players):
                await self.send(p, {"type": "notice", "message": "Both players need to read their phones first."})
                return
            if room.solved:
                await self.send(p, {"type": "notice", "message": "Your garden is already unlocked!"})
                return
            if room.progress != which:
                await self.announce(room, "Not quite! The Moon needs to glow before the Star.", "toast")
                return
            room.progress += 1
            if room.progress == 1:
                await self.announce(room, "The Moon is shining! Tosh Tosh, find the rose Star.", "toast")
            else:
                room.solved = True
                if "first-call" not in room.memories:
                    room.memories.append("first-call")
                await self.announce(room, "A new memory unlocked: The First Call!", "celebration")
        else:
            return
        room.last_activity = time.time()
        self.changed = True
        self.save()
        await self.broadcast(room)

    def move(self, room: Room, p: Player, dt: float) -> None:
        dx, dz = p.dx, p.dz
        mag = math.hypot(dx, dz)
        if mag > 1:
            dx, dz = dx / mag, dz / mag
        x = max(-12.35, min(12.35, p.x + dx * SPEED * dt))
        z = max(-3.55, min(3.85, p.z + dz * SPEED * dt))
        # The bedrooms are separate until the cooperative door puzzle is solved.
        if not room.solved:
            if p.x < 0:
                x = min(x, -3.68)
            else:
                x = max(x, 3.68)
        if x != p.x or z != p.z:
            p.x, p.z = x, z
            room.last_activity = time.time()
            self.changed = True

    async def tick(self) -> None:
        elapsed_save = 0.0
        try:
            while self.running:
                start = time.monotonic()
                for room in tuple(self.rooms.values()):
                    if any(p and p.online for p in room.players):
                        for p in room.players:
                            if p and p.online:
                                self.move(room, p, TICK)
                        await self.broadcast(room)
                elapsed_save += TICK
                if elapsed_save >= 3:
                    self.save()
                    elapsed_save = 0
                await asyncio.sleep(max(0.0, TICK - (time.monotonic() - start)))
        except asyncio.CancelledError:
            self.save()
            raise


def make_app(game: Game | None = None) -> web.Application:
    game = game or Game()
    app = web.Application(client_max_size=16 * 1024)
    game_key = web.AppKey("game", Game)
    ticker_key = web.AppKey("ticker", asyncio.Task)
    app[game_key] = game

    async def health(_request: web.Request) -> web.Response:
        return web.json_response({"ok": True, "rooms": len(game.rooms), "version": "0.1.0"})

    async def index(_request: web.Request) -> web.FileResponse:
        return web.FileResponse(PUBLIC / "index.html", headers={
            "Cache-Control": "no-cache",
            "X-Robots-Tag": "noindex, nofollow, noarchive",
            "X-Content-Type-Options": "nosniff",
        })

    async def robots(_request: web.Request) -> web.Response:
        return web.Response(text="User-agent: *\nDisallow: /\n", content_type="text/plain")

    async def private_photo(request: web.Request) -> web.StreamResponse:
        """Only the two room members can fetch the private memory image."""
        code = request.headers.get("X-Room-Code", "").upper().strip()
        token = request.headers.get("X-Room-Token", "")
        room = game.rooms.get(code)
        if (not room or not token or
                not any(p and secrets.compare_digest(p.token, token) for p in room.players)):
            raise web.HTTPForbidden(text="A valid room membership is required")
        photo_path = PRIVATE / "memories" / "first-call.jpg"
        if not photo_path.is_file():
            raise web.HTTPNotFound(text="No photo has been added yet")
        return web.FileResponse(photo_path, headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
        })

    async def socket(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(heartbeat=20, max_msg_size=4096)
        await ws.prepare(request)
        room: Room | None = None
        player: Player | None = None
        slot: int | None = None
        try:
            async for msg in ws:
                if msg.type != WSMsgType.TEXT:
                    if msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                        break
                    continue
                try:
                    event = json.loads(msg.data)
                    if not isinstance(event, dict):
                        continue
                except json.JSONDecodeError:
                    await ws.send_json({"type": "error", "message": "Invalid message."})
                    continue
                action = event.get("type")
                if room is None:
                    try:
                        if action == "create":
                            room, player = game.create()
                            slot = 0
                        elif action == "join":
                            room, player, slot = game.join(str(event.get("code", "")),
                                                           str(event.get("token", "")) or None)
                        else:
                            await ws.send_json({"type": "error", "message": "Create or join a room first."})
                            continue
                    except (ValueError, RuntimeError) as exc:
                        await ws.send_json({"type": "error", "message": str(exc)})
                        continue
                    if player.socket and player.socket is not ws and not player.socket.closed:
                        await player.socket.close(code=4000, message=b"Reconnected elsewhere")
                    player.socket, player.online = ws, True
                    player.dx, player.dz = 0.0, 0.0
                    await ws.send_json({"type": "welcome", "room": room.public(),
                                        "slot": slot, "token": player.token})
                    await game.broadcast(room)
                elif action == "input" and player:
                    player.dx = finite_axis(event.get("x"))
                    player.dz = finite_axis(event.get("z"))
                elif action == "interact" and player and slot is not None:
                    target = event.get("target")
                    if isinstance(target, str):
                        await game.interact(room, player, slot, target)
        finally:
            if player and player.socket is ws:
                player.online, player.dx, player.dz = False, 0.0, 0.0
                player.socket = None
                game.changed = True
                game.save()
                if room:
                    await game.broadcast(room)
        return ws

    app.router.add_get("/health", health)
    app.router.add_get("/ws", socket)
    app.router.add_get("/", index)
    app.router.add_get("/robots.txt", robots)
    app.router.add_get("/private-photo/first-call", private_photo)
    app.router.add_static("/assets", PUBLIC / "assets")
    async def javascript(_request: web.Request) -> web.FileResponse:
        return web.FileResponse(PUBLIC / "game.js")

    async def stylesheet(_request: web.Request) -> web.FileResponse:
        return web.FileResponse(PUBLIC / "styles.css")

    async def personalization(_request: web.Request) -> web.FileResponse:
        return web.FileResponse(PUBLIC / "personalization.json")

    app.router.add_get("/game.js", javascript)
    app.router.add_get("/styles.css", stylesheet)
    app.router.add_get("/personalization.json", personalization)

    async def on_startup(application: web.Application) -> None:
        application[ticker_key] = asyncio.create_task(game.tick())

    async def on_cleanup(application: web.Application) -> None:
        game.running = False
        ticker = application.get(ticker_key)
        if ticker is None:
            return
        ticker.cancel()
        try:
            await ticker
        except asyncio.CancelledError:
            pass
        game.save()

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    web.run_app(make_app(), host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
