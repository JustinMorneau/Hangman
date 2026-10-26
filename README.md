# Hangman

A networked Hangman game. A Python/Flask server holds all the game logic and
the hidden word; a browser client plays through a JSON REST API. The word
never leaves the server until a game ends.

**Live app:** https://hangman-fo4n.onrender.com

- [Playing the game](#playing-the-game)
- [Running locally](#running-locally)
- [Running the tests](#running-the-tests)
- [REST API](#rest-api)
- [How it works](#how-it-works)
- [Deployment (Render)](#deployment-render)
- [Scope and deviations from the specification](#scope-and-deviations-from-the-specification)

## Playing the game

Open the [live app](https://hangman-fo4n.onrender.com) or a local server.
On the free hosting plan, the first visit after a quiet period can take up
to a minute while the server wakes up.

1. Choose **Easy**, **Medium**, or **Hard**. The page starts a Medium game
   when it opens.
2. Guess a letter by clicking it on the on-screen keyboard or typing it.
   - A correct letter appears in every matching position and its key turns blue.
   - A wrong letter draws the next part of the figure, and its key turns red
     and is crossed out. Wrong letters are also listed under **Misses**.
   - Letters already guessed are disabled; typing one again does nothing.
3. You win by finding every letter before six wrong guesses. On the sixth
   wrong guess the figure is complete and the game is lost; the word is then
   shown, with the letters you missed in red.
4. Click **New game** at any time to start again with the selected
   difficulty. The page does not reload.

The layout works on phones, tablets, and desktops, can be played entirely
from the keyboard, and follows the system's light or dark mode.

## Running locally

Requires Python 3.10 or newer and Git.

```bash
git clone https://github.com/JustinMorneau/Hangman.git
cd Hangman
python -m venv .venv
source .venv/Scripts/activate        # Windows (Git Bash)
# .venv\Scripts\activate             # Windows (Command Prompt or PowerShell)
# source .venv/bin/activate          # macOS / Linux
python -m pip install -r requirements-dev.txt
python server.py
```

Open <http://127.0.0.1:5000>. Stop the server with Ctrl+C.

On some systems the Python command is `python3` or `py` instead of `python`.
`python server.py` starts Flask's development server with debug mode on; it
is for local use only (see [Deployment](#deployment-render)).

## Running the tests

```bash
python -m playwright install chromium   # once, for the browser tests
python -m pytest -v
```

Expected result: **171 passed**. If Playwright's browser is not installed,
the 18 browser tests are skipped and the rest still run.

| File | Tests | Covers |
|---|---|---|
| `tests/test_word_manager.py` | 28 | Word list loading, validation, random selection |
| `tests/test_game.py` | 42 | Game engine rules, without a server |
| `tests/test_server.py` | 55 | Every endpoint, status code, and malformed request |
| `tests/test_client.py` | 7 | The page is served; the client has no game logic or words |
| `tests/test_end_to_end.py` | 6 | 120 full games with rules checked at every step; real HTTP; concurrency |
| `tests/test_deployment.py` | 7 | Render configuration and a smoke test against a live server |
| `tests/test_docs.py` | 8 | This README matches the real API responses, error messages, and files |
| `tests/test_browser.py` | 18 | Real Chromium: input, drawing, win/loss, new game, layout at four sizes |

To check a running server (local or deployed) by playing real games:

```bash
python smoke_test.py http://127.0.0.1:5000
python smoke_test.py https://hangman-fo4n.onrender.com
```

`TESTING.md` has the manual browser checklist, the results, and a log of
every bug found and fixed.

## REST API

All requests and responses use JSON. Send `Content-Type: application/json`
with every request that has a body.

| Method | Endpoint | Purpose | Success |
|---|---|---|---|
| `POST` | `/api/games` | Create a new game | `201 Created` |
| `GET` | `/api/games/{game_id}` | Get the current state of a game | `200 OK` |
| `POST` | `/api/games/{game_id}/guess` | Guess one letter | `200 OK` |

### Game state

Every successful response is a game state:

| Field | Type | Meaning |
|---|---|---|
| `game_id` | string | Unique id for this game (16 hex characters) |
| `difficulty` | string | `easy`, `medium`, or `hard` |
| `pattern` | string | The word with unguessed letters as `_`, separated by spaces |
| `word_length` | integer | Number of letters in the word |
| `guessed_letters` | list | Every accepted guess, in order |
| `correct_letters` | list | Guesses that are in the word |
| `incorrect_letters` | list | Guesses that are not in the word |
| `remaining_guesses` | integer | Wrong guesses left (6 minus misses) |
| `max_incorrect` | integer | Wrong guesses allowed per game (6) |
| `status` | string | `playing`, `won`, or `lost` |
| `correct` | boolean | Guess responses only: whether that letter was in the word |
| `word` | string | **Only after the game ends** (`won` or `lost`) |

### Create a game

`difficulty` is optional and defaults to `medium`; it is case-insensitive.

```http
POST /api/games
Content-Type: application/json

{"difficulty": "easy"}
```

Response `201 Created`:

```json
{
  "correct_letters": [],
  "difficulty": "easy",
  "game_id": "e8ddf8abc9ecc7ba",
  "guessed_letters": [],
  "incorrect_letters": [],
  "max_incorrect": 6,
  "pattern": "_ _ _ _ _",
  "remaining_guesses": 6,
  "status": "playing",
  "word_length": 5
}
```

### Guess a letter

`letter` must be one letter `a`-`z`; uppercase is accepted.

```http
POST /api/games/e8ddf8abc9ecc7ba/guess
Content-Type: application/json

{"letter": "p"}
```

Response `200 OK` (a correct guess):

```json
{
  "correct": true,
  "correct_letters": ["p"],
  "difficulty": "easy",
  "game_id": "e8ddf8abc9ecc7ba",
  "guessed_letters": ["p"],
  "incorrect_letters": [],
  "max_incorrect": 6,
  "pattern": "_ p p _ _",
  "remaining_guesses": 6,
  "status": "playing",
  "word_length": 5
}
```

After a wrong guess, `correct` is `false`, the letter is added to
`incorrect_letters`, and `remaining_guesses` drops by one. When the last
letter is found, `status` becomes `won` and `word` is included:

```json
{
  "correct": true,
  "correct_letters": ["p", "a", "l", "e"],
  "difficulty": "easy",
  "game_id": "e8ddf8abc9ecc7ba",
  "guessed_letters": ["p", "z", "a", "l", "e"],
  "incorrect_letters": ["z"],
  "max_incorrect": 6,
  "pattern": "a p p l e",
  "remaining_guesses": 5,
  "status": "won",
  "word": "apple",
  "word_length": 5
}
```

### Get a game

```http
GET /api/games/e8ddf8abc9ecc7ba
```

Response `200 OK`: the same game state, without the `correct` field.

### Errors

Errors return a JSON body with one field, `error`, and the game is never
changed by a rejected request.

| Status | When | Example `error` |
|---|---|---|
| `400` | Body is missing, not JSON, or not a JSON object | `Request body must be a JSON object, e.g. {"difficulty": "medium"}.` |
| `400` | Difficulty is not easy, medium, or hard | `Invalid difficulty 'expert'. Choose one of: easy, medium, hard.` |
| `400` | `letter` field is missing | `Missing required field "letter".` |
| `400` | `letter` is not exactly one letter a-z | `Guess must be a single letter a-z.` |
| `404` | No game with that id (or the server restarted) | `Game 'abc123' not found.` |
| `405` | Wrong HTTP method for the URL | `The method is not allowed for the requested URL.` |
| `409` | Letter was already guessed in this game | `The letter 'e' was already guessed.` |
| `409` | The game is already won or lost | `The game is already won.` |
| `413` | Request body larger than 16 KB | `Request body is too large (limit 16384 bytes).` |

```json
{
  "error": "The letter 'e' was already guessed."
}
```

### Playing with curl

Replace `GAME_ID` with the `game_id` from the first response. These work in
Git Bash, macOS, and Linux. In Windows PowerShell, type `curl.exe` instead
of `curl`.

```bash
curl -X POST https://hangman-fo4n.onrender.com/api/games \
     -H "Content-Type: application/json" -d '{"difficulty":"hard"}'

curl -X POST https://hangman-fo4n.onrender.com/api/games/GAME_ID/guess \
     -H "Content-Type: application/json" -d '{"letter":"e"}'

curl https://hangman-fo4n.onrender.com/api/games/GAME_ID
```

## How it works

```
 Browser (static/)                 Flask server (server.py)
 ┌──────────────────────┐  fetch   ┌────────────────────────────────┐
 │ index.html           │  JSON    │ REST API                       │
 │ style.css            │ ───────▶ │ GameStore: games in memory     │
 │ app.js: draws state, │ ◀─────── │   └ HangmanGame (game.py)      │
 │ sends guesses        │          │ WordManager (word_manager.py)  │
 └──────────────────────┘          │   └ words/easy|medium|hard.txt │
                                   └────────────────────────────────┘
```

- **The server is authoritative.** `game.py` decides whether each guess is
  right, wrong, a duplicate, a win, or a loss. `app.js` only sends letters
  and draws whatever state comes back; it holds no word lists and makes no
  game decisions.
- **The word is protected in one place.** Every response is built from
  `HangmanGame.to_dict()`, which adds `word` only when the game has ended.
- **The game engine is independent.** `game.py` and `word_manager.py` do not
  import Flask, so they are tested without a server.
- **Games are kept in memory** in a `GameStore` with a lock, so simultaneous
  requests cannot corrupt a game. At most 10,000 games are kept; the oldest
  are dropped first.
- **Word lists** are plain text, one word per line, `#` for comments. Words
  must be letters a-z only and are checked when the server starts.
  Duplicates are removed. Words longer than 12 letters are rejected by the
  tests because the layout is tested only up to 12.

### Project files

| Path | Purpose |
|---|---|
| `game.py` | Game engine: `HangmanGame` |
| `word_manager.py` | Loads and validates word lists; random word by difficulty |
| `words/` | `easy.txt`, `medium.txt`, `hard.txt` (40 words each) |
| `server.py` | Flask app, REST API, and game storage |
| `static/` | Browser client: `index.html`, `style.css`, `app.js` |
| `tests/` | Automated tests; `conftest.py` holds the shared live server |
| `smoke_test.py` | Plays real games against a running server |
| `render.yaml`, `.python-version` | Render deployment configuration |
| `requirements.txt` | Packages the app needs (installed on Render) |
| `requirements-dev.txt` | Those plus pytest and Playwright |
| `TESTING.md` | Test guide, manual checklist, results, bug log |
| `TODO.md` | Implementation roadmap |
| `Hangman_Project_Specification.md` | Original specification, with implementation notes |

## Deployment (Render)

The app runs on [Render](https://render.com) as a free Python web service,
configured by `render.yaml`.

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
2. Sign in at <https://dashboard.render.com> with GitHub and allow Render to
   access the repository.
3. Click **New** → **Blueprint**, select the repository, and click
   **Deploy Blueprint**.
4. When the service shows **Live**, copy its `https://….onrender.com` URL
   from the top of the service page.
5. Verify it: `python smoke_test.py https://hangman-fo4n.onrender.com`

Later pushes to `main` redeploy automatically.

### Why these settings

- **Gunicorn** is a production web server; Flask's built-in server is for
  development only. Gunicorn does not run on Windows, so `requirements.txt`
  skips it there and `python server.py` is used locally instead.
- **One worker.** Games live in the server process's memory. A second worker
  would not know the first one's games, and guesses would randomly get 404s.
  Four threads let the single worker serve several requests at once.
- **`$PORT` and `0.0.0.0`.** Render chooses the port and routes outside
  traffic to it, so the server listens on all interfaces.
- **HTTPS** is provided by Render on the `onrender.com` URL.
- **Relative API paths.** The browser calls `/api/games`, not a full URL, so
  the same code works locally and deployed.
- **`plan: free`** is set explicitly because Render uses a paid plan when
  the field is missing.

### Known limitations

- **Cold starts.** Free services sleep after about 15 minutes without
  traffic; the next request can take up to a minute.
- **Games are not saved.** A restart, redeploy, or sleep clears all games. A
  guess in a cleared game shows "This game is no longer on the server. Start
  a new game to keep playing."
- **Single instance.** The in-memory design does not scale to multiple
  servers; that would need a database.

## Scope and deviations from the specification

`Hangman_Project_Specification.md` describes a larger system. This project
implements only its **game engine, word management, Flask REST server, and
browser client**, plus testing and cloud deployment.

**Not implemented (out of scope):** the terminal client, automated bots,
evaluation mode, scoring, the leaderboard, anti-cheating safeguards, logging
and replay, and the specification's future extensions.

**Deviations** (each also noted in the specification's implementation notes):

| Specification | This project | Reason |
|---|---|---|
| Duplicate guesses "ignored or rejected" | Rejected with `409 Conflict`; state unchanged | A clear signal to API clients; the browser disables guessed keys so players never see it |
| Example responses list a few fields | Responses include the full game state (table above), and guess responses add `correct` | The browser needs all of it to draw the page without game logic of its own |
| Create request includes `difficulty` | `difficulty` is optional (default `medium`) and case-insensitive | Convenience; invalid values are still rejected with `400` |
| No error format given | Every error is `{"error": "..."}` with a fitting status code | Consistent handling in the browser and tests |
| No request size limit | Bodies over 16 KB get `413` | Protects the public server |
| Suggested structure has no `word_manager.py` or `tests/` | Word loading is a separate module; tests live in `tests/` | Keeps the engine small and testable |
| Not specified | `smoke_test.py`, `render.yaml`, `.python-version`, `requirements-dev.txt` | Deployment and verification |
