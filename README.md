# Hangman

A networked Hangman game: a Python/Flask server that holds all game logic,
and a browser client that talks to it through a JSON REST API. The hidden
word stays on the server until a game ends.

**Live app:** https://hangman-fo4n.onrender.com

> Full documentation (API reference, examples, project structure) is added
> in Phase 6. See `TESTING.md` for how the project is tested.

## Run locally

Requires Python 3.10 or newer.

```bash
git clone https://github.com/JustinMorneau/Hangman.git
cd Hangman
python -m venv .venv
source .venv/Scripts/activate        # Git Bash on Windows
# source .venv/bin/activate          # macOS / Linux
python -m pip install -r requirements-dev.txt
python server.py
```

Open <http://127.0.0.1:5000>. Run the tests with `python -m pytest -v`.

## Deployment (Render)

The app is deployed to [Render](https://render.com) as a free Python web
service, configured by `render.yaml` in the repository root.

| Setting | Value |
|---|---|
| Plan | Free |
| Python | 3.12 (from `.python-version`) |
| Build command | `pip install -r requirements.txt` |
| Start command | `gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 server:app` |
| Health check | `GET /` |
| Auto-deploy | On every push to `main` |

### Deploy steps

1. Push the repository to GitHub.
2. Sign in at <https://dashboard.render.com> with GitHub, and allow Render to
   access the `Hangman` repository.
3. Click **New** → **Blueprint**, select the repository, and click
   **Deploy Blueprint**. Render reads `render.yaml` and creates the service.
4. When the deploy log shows the service is live, open the
   `https://….onrender.com` URL shown on the service page.
5. Verify it: `python smoke_test.py https://hangman-fo4n.onrender.com`

### Why these settings

- **Gunicorn** is a production web server. Flask's built-in server
  (`python server.py`) is for development only and runs with debug mode on.
  Gunicorn does not run on Windows, so `requirements.txt` skips it there.
- **One worker.** Games are kept in the server process's memory. With two
  workers, a guess could reach the process that never created the game and
  get a 404. One worker with four threads still serves several requests at
  once; a lock keeps each game consistent.
- **`$PORT` and `0.0.0.0`.** Render chooses the port and routes outside
  traffic to it; the server must listen on all interfaces, not `localhost`.
- **HTTPS** is provided by Render automatically on the `onrender.com` URL.
- **Relative API paths.** The browser calls `/api/games`, not a full URL,
  so the same code works locally and when deployed.

### Known limitations

- **Cold starts.** Free services sleep after about 15 minutes without
  traffic. The next visit wakes the server, which can take up to a minute.
- **Games are not saved.** Games live in memory, so any restart, redeploy,
  or sleep clears them. A guess in a cleared game shows "This game is no
  longer on the server. Start a new game to keep playing."
- **Single instance.** The in-memory design does not scale across multiple
  servers. A database would be needed for that (out of scope).

## Project files

| File | Purpose |
|---|---|
| `game.py` | Game engine (no Flask dependency) |
| `word_manager.py` | Loads and validates word lists; random word by difficulty |
| `words/` | `easy.txt`, `medium.txt`, `hard.txt` |
| `server.py` | Flask app and REST API |
| `static/` | Browser client: `index.html`, `style.css`, `app.js` |
| `tests/` | Automated tests (pytest, Playwright) |
| `smoke_test.py` | Plays real games against a local or deployed server |
| `render.yaml`, `.python-version` | Render deployment configuration |
| `requirements.txt` | Runtime dependencies (installed on Render) |
| `requirements-dev.txt` | Runtime plus test dependencies |
