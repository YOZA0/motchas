# Our Little Universe — Mustafa & Tosh Tosh ♡

**A working, original 3D multiplayer anniversary-game foundation.** This is **Milestone 1 / Chapter 1**, not the completed seven-chapter game.

Two separate browsers (including two iPads on different networks after deployment) can connect using a private six-character room code. Each person moves their own cute 3D character around a pastel bedroom, reads a unique phone clue, cooperates to activate the Moon and Star switches, unlocks a shared garden and collects the first scrapbook memory.

The first version deliberately uses an original **WebGL renderer with no external JavaScript dependencies** rather than downloading engine packages. This makes the project quick to run, portable, and playable without build tooling. The multiplayer backend uses Python + `aiohttp`.

**To publish this as a real website, open [DEPLOY_TO_WEB.md](DEPLOY_TO_WEB.md).** It includes the GitHub + Render procedure and important free-hosting save limitations.

## 1. Run on your computer

Install **Python 3.10+**. From this project folder:

```bash
python -m pip install -r requirements.txt
python server.py
```

Open **http://localhost:8080** in two separate browser windows, click **Create our world** in the first, then enter its code in the second. You can also click **ROOM** to copy an invitation link.

### Controls

| Device | Control |
| --- | --- |
| PC | WASD or arrow keys to walk; E to interact |
| iPad / touch | On-screen left joystick; right **INTERACT** button |
| Both | Drag the background to rotate camera; pinch (touch) or scroll (PC) to zoom |
| All | Open the **Memories** button to view your scrapbook |

**If you want to test locally on an iPad:** both devices must be on the same Wi-Fi, and you must open the computer's LAN IP and port 8080 (for example `http://192.168.1.10:8080`, not `localhost`). Your firewall must allow this port. An HTTPS deployment is needed for simple use across separate networks.

## 2. The first cooperative puzzle

1. Mustafa creates the world and shares his room code.
2. Tosh Tosh joins on a different device.
3. Both find their glowing phone (on the small writing desk) and tap **INTERACT**.
4. Mustafa learns which symbol goes first. Tosh Tosh learns the symbols' colors.
5. Mustafa walks to the lavender **Moon** switch near the center and activates it.
6. Tosh Tosh walks to the rose **Star** switch and activates it.
7. The magical barriers vanish; both can meet in the shared garden. The first memory is stored in the book.

A player reconnects to their original character automatically when using the same browser and room code. Progress is saved in `data/rooms.json` on the server.

## 3. Add personal photos later

Place the photo in:

```text
private_assets/memories/first-call.jpg
```

The room members will see it in the memory book the next time they connect; **no configuration edit is required**. The private image is served by a room-token-protected endpoint and is **not** stored in the public `web` folder. Other photos, actual couple character designs, and personal dialogue can be added when the files are provided. **Do not upload private photos to a public Git repository.** Also keep sensitive personal letters out of public `web/personalization.json` until private storage is added for those letters.

## 4. Deploy for two iPads in different locations

This is **one service**, serving the webpage and WebSocket from the same domain, so you don't need separate frontend/backend services.

A `Dockerfile` and `render.yaml` are included as a starting point for Render. Push the code to a **private** repository, create a new web service on your host, and use the Dockerfile. The host must support persistent HTTP WebSocket connections and HTTPS. Share the HTTPS game URL and private six-character room code.

**Persistence warning:** `data/rooms.json` is reliable on your local computer, but many cloud hosts (including ephemeral containers) remove local files during redeployment or restarting. To preserve memories in production, configure persistent storage (`DATA_DIR`) on the host **or** migrate rooms/memories to a database before relying on them. A hosted persistent disk may incur cost. Do not promise save durability on an ephemeral free plan.

## 5. Architecture

```
server.py                 Authoritative movement, 2-player rooms, WebSocket, puzzle, persistence
web/index.html            Responsive menus, HUD, dialogues, scrapbook
web/styles.css            Pastel visual identity, iPad touch control layout
web/game.js               Real-time networking, touch inputs, original WebGL 3D renderer
web/personalization.json  Editable characters/story/photo references
private_assets/memories/  Private photo storage (membership-checked image endpoint)
```

Main server safeguards: full two-player capacity; room token for re-entry; room membership; server-controlled movement speed and room boundaries; server-side interaction-distance checks; co-op puzzle order; persistent puzzle status; disconnected players retain their slot.

## 6. Roadmap (not yet implemented)

- Milestone 2: enhance animations, collision, touch usability, iPad Safari performance, art and character customization.
- Chapter 2: **Our Little Kitchen** — synchronized ingredient collection, baking and cake decoration.
- Chapter 3: **A Picture of Us** — synchronized painting canvas with undo, size, palette and shared art storage.
- Chapter 4: **Just You and Me** — cooperative maze, friendly race, personal question game and hide-and-seek.
- Chapter 5: **Our Little World** — nighttime garden, flowers, hidden stars, bridges and co-op switches.
- Chapter 6: **Our Memory Book** — full scrapbook with every story photo, collectible, painting and caption.
- Chapter 7: **Forever Starts Here** — wedding garden, cutscene, character kiss, letter and replay.

**Current limitations:** Chapter 1 only, procedural placeholder character designs (not personalized yet), no sound or polished scripted animation, no physical collision with furniture, room links work only if server is reachable, photo file not included. Camera and movement were implemented in real 3D, but full testing on two actual iPads requires access to those devices.
