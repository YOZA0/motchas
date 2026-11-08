# Publish Our Little Universe as a real website

This project is a **single full-stack website**: the Python server provides both the 3D game webpage and the real-time two-player WebSocket connection. Do **not** deploy only the `web/` folder to a static-site host — joining rooms requires the running server.

## Option A — Render (recommended for the first online test)

1. Download and extract the complete project ZIP. Keep the folder structure intact, including `web/`, `private_assets/`, `server.py`, `Dockerfile`, `requirements.txt`, and `render.yaml`.
2. Sign in to [GitHub](https://github.com/) and create a **private repository** named `our-little-universe`. Upload the **contents** of the extracted project folder, preserving folder structure (or publish the folder using GitHub Desktop). Do not include your private photos, secrets, or the local `data/rooms.json` file.
3. Sign in to [Render](https://dashboard.render.com/), choose **New → Blueprint**, connect your GitHub repository, and approve deployment of the `render.yaml` blueprint. If you prefer **New → Web Service**, select the repository, choose **Docker** as the runtime, and select a suitable instance plan. The included `Dockerfile` already starts the game server and respects Render's `PORT` variable.
4. Once the Render service displays **Live**, click its public `https://....onrender.com` URL. (The exact hostname is assigned by Render; it is **not** known before deployment.)
5. On the first iPad, open the HTTPS link in Safari and tap **Create our world**. Share the link/room code with Tosh Tosh. On her iPad, open the same HTTPS site and join with the code.

The server's `/health` route should respond with `{"ok":true,...}` when it is healthy. Both the page and WebSocket run on the **same** public origin, so no separate frontend setup or WebSocket URL configuration is required.

**Important on Render Free:** Free instances may sleep after 15 minutes of inactivity and take some time to wake. Their local files are **ephemeral**: room codes, puzzles, and memories saved by this prototype can be lost after a restart or redeployment. If a room disappears, create a new one. **Before adding precious personal photos or relying on saved memories, migrate to a durable database or use persistent storage on an eligible paid host.**

## Option B — Any Docker-compatible web host

The project includes a portable `Dockerfile`. The host must:

- Support HTTPS, long-lived WebSocket connections, and a single running instance.
- Expose the HTTP port specified by environment variable `PORT` (defaults to `8080`).
- Have writable storage for `DATA_DIR`; for durable progress use a persistent volume or a database.

Quick local container check, if Docker is installed:

```sh
docker build -t our-little-universe .
docker run --rm -p 8080:8080 our-little-universe
```

Then open `http://localhost:8080`.

## About privacy

- This version has a **private room code**, not a password-protected website. Anyone who knows a room code can join an unoccupied player slot, so share it only with your partner.
- The site's HTML asks search engines not to index it, but that **does not make the website private**.
- The future memory photo is served through a room-member-token check; keep photos outside public `web/` and outside the code repository. Additional safeguards are recommended before storing sensitive photos or letters.
- The game is **Chapter 1**, not the completed seven-chapter game.

## Where the website files are

- `web/index.html` — webpage and game UI
- `web/styles.css` — interface styles
- `web/game.js` — 3D game renderer, controls and WebSocket client
- `server.py` — web and multiplayer server
- `Dockerfile`, `render.yaml`, `requirements.txt` — hosting configuration

**Do not double-click `web/index.html` and expect multiplayer.** Use the Python server locally or deploy the full project online.
