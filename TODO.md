# TODO — Hangman Client/Server Project

This file is the implementation roadmap for the Hangman project.

The authoritative system requirements are defined in `Hangman_Project_Specification.md`.

## Project Scope

This project implements **only** the Hangman server and the browser-based client:

1. Game engine and word management
2. Flask server and REST API
3. Browser-based client
4. Testing and debugging
5. Cloud deployment

The original specification also describes a terminal client, automated bots, evaluation mode, scoring, a leaderboard, anti-cheating safeguards, and logging/replay. Those features are **out of scope** and are listed at the end of this file for reference only. Do not implement them.

## Implementation Rules

- Implement one phase at a time.
- Complete and test all items in the current phase before moving to the next phase.
- Do not change the architecture or REST API defined in `Hangman_Project_Specification.md` unless necessary.
- If a deviation is necessary, document it in the README and update the specification.
- Keep the game engine independent from Flask and the browser UI.
- The server must remain authoritative. The browser must not contain its own game engine.
- Never expose the hidden word before a game ends.
- Add tests as each phase is implemented rather than postponing testing until the end.
- The project should remain runnable after every completed phase.

---

## Phase 1 — Game Engine and Word Management

### Tasks

#### Project skeleton

- [x] Create the project directory structure (`game.py`, `word_manager.py`, `server.py`, `static/`, `words/`, `tests/`).
- [x] Add `requirements.txt`.
- [x] Add `words/easy.txt`.
- [x] Add `words/medium.txt`.
- [x] Add `words/hard.txt`.

#### Word management

- [x] Create a word-loading module (`word_manager.py`).
- [x] Load the Easy, Medium, and Hard word lists.
- [x] Validate that loaded words contain only alphabetic characters.
- [x] Normalize words to lowercase and remove accidental duplicates.
- [x] Support random word selection by difficulty.
- [x] Return a clear error for an invalid difficulty.

#### Game engine

- [x] Create `game.py` with a `HangmanGame` class.
- [x] Store the hidden word internally.
- [x] Track the difficulty level.
- [x] Validate guesses: exactly one alphabetic letter, case-insensitive.
- [x] Track all guessed letters.
- [x] Track correct and incorrect letters.
- [x] Track the maximum (6) and remaining incorrect guesses.
- [x] Detect and reject duplicate guesses without changing game state.
- [x] Generate the current word pattern (e.g. `_ e _ _ e`).
- [x] Detect wins.
- [x] Detect losses.
- [x] Implement status values `playing`, `won`, and `lost`.
- [x] Prevent further guesses after a game ends.
- [x] Implement a method that returns a client-safe game-state dictionary.
- [x] Reveal the answer only after the game ends.
- [x] Keep the engine free of any Flask or browser dependencies.

#### Tests

- [x] Unit tests for word loading, validation, deduplication, and selection by difficulty.
- [x] Unit tests for invalid difficulty.
- [x] Unit tests for correct guesses, incorrect guesses, invalid guesses, and duplicate guesses.
- [x] Unit tests for win and loss paths.
- [x] Unit tests confirming guesses are rejected after the game ends.
- [x] Unit tests confirming the state dictionary omits the word while `playing`.

### Completion Criteria

The game engine and word manager can be tested entirely without running a web server.

A random word can be requested reliably from each difficulty level, and invalid difficulty values are rejected cleanly.

All core rules are covered by unit tests.

---

## Phase 2 — Flask Server and REST API

### Tasks

- [x] Create `server.py`.
- [x] Configure Flask.
- [x] Add in-memory storage for active games.
- [x] Generate unique game IDs.
- [x] Implement `POST /api/games` (create a new game).
- [x] Implement `GET /api/games/{game_id}` (retrieve current game state).
- [x] Implement `POST /api/games/{game_id}/guess` (submit a letter guess).
- [x] Accept and return JSON only; return JSON for errors as well.
- [x] Validate the difficulty input.
- [x] Validate the guess input (missing body, non-JSON body, missing `letter`, multiple letters, non-letters).
- [x] Decide and document how duplicate guesses are reported (rejected with an error status, state unchanged).
- [x] Reject guesses on finished games with an appropriate status code.
- [x] Return appropriate HTTP status codes (`201`, `200`, `400`, `404`, `409` as applicable).
- [x] Handle unknown game IDs with `404`.
- [x] Maintain separate state for each game.
- [x] Ensure the hidden word is never included in responses while `status` is `playing`.
- [x] Serve the browser client (`static/index.html`) from the Flask app at `/`.

### Tests

- [x] API tests for creating games at all three difficulty levels.
- [x] API tests for correct, incorrect, duplicate, and invalid guesses.
- [x] API tests for win and loss paths through the API.
- [x] API tests for unknown game IDs and malformed requests.
- [x] API tests confirming two concurrent games keep independent state.
- [x] API tests confirming no response contains the word while `playing`.

### Completion Criteria

A complete Hangman game can be played using only `curl` or another HTTP client.

The browser client is not required for this phase.

---

## Phase 3 — Browser Client

### Tasks

- [x] Create `static/index.html`.
- [x] Create `static/style.css`.
- [x] Create `static/app.js`.
- [x] Add a difficulty selector (Easy, Medium, Hard).
- [x] Add a New Game button.
- [x] Display the current word pattern.
- [x] Display previously guessed letters.
- [x] Display incorrect letters.
- [x] Display remaining incorrect guesses.
- [x] Add an on-screen alphabet keyboard.
- [x] Support guessing letters with the physical keyboard.
- [x] Disable already-guessed letters.
- [x] Use `fetch()` for all communication with the REST API.
- [x] Update the display from the server's response after every guess.
- [x] Draw the Hangman figure (SVG or HTML elements).
- [x] Update the drawing as incorrect guesses accumulate.
- [x] Display win and loss messages, including the revealed word after the game ends.
- [x] Disable guessing after the game ends.
- [x] Start another game without reloading the page.
- [x] Display server and network errors gracefully.
- [x] Make the interface usable on common desktop and mobile browser sizes.

### Completion Criteria

A human player can play a full server-hosted game from a browser.

No game logic or hidden word is stored in browser-side JavaScript; the browser only displays what the server returns.

---

## Phase 4 — Testing and Debugging

### Tasks

- [x] Review and complete unit tests for the game engine and word manager.
- [x] Review and complete REST API tests.
- [x] Test starting games at all three difficulty levels.
- [x] Test correct and incorrect guesses.
- [x] Test repeated and invalid guesses.
- [x] Test winning and losing games.
- [x] Test starting a new game after completing one.
- [x] Test invalid API requests (bad JSON, missing fields, bad difficulty, unknown IDs).
- [x] Test that the hidden word is not exposed during active gameplay.
- [x] Add an end-to-end automated test that plays a complete game through the API.
- [x] Manually test the browser client: each difficulty, on-screen and physical keyboard input, drawing updates, win/loss messages, and new-game flow.
- [x] Check the browser's network tab to confirm no response contains the word while `playing`.
- [x] Test the browser layout at desktop and mobile sizes.
- [x] Record manual browser test results (checklist) in the README or a `TESTING.md` file.
- [x] Fix any bugs found and add a regression test for each fix where practical.

### Completion Criteria

All automated tests pass.

The major user flows and failure cases are covered by automated or documented manual tests.

---

## Phase 5 — Cloud Deployment

### Tasks

- [ ] Add `gunicorn` to `requirements.txt`.
- [ ] Ensure `debug=True` is used only for local development, never in production.
- [ ] Verify the app runs locally under Gunicorn: `gunicorn --bind 127.0.0.1:5000 --workers 1 server:app`.
- [ ] Use a single worker so all requests share the same in-memory game store.
- [ ] Add a `render.yaml` Blueprint (or equivalent service settings) with:
  - Build command: `pip install -r requirements.txt`
  - Start command: `gunicorn --bind 0.0.0.0:$PORT --workers 1 server:app`
- [ ] Make sure the browser client uses relative API paths (e.g. `/api/games`) so it works on the public host.
- [ ] Push the project to GitHub.
- [ ] Create the Render web service from the GitHub repository.
- [ ] Confirm the app is reachable at a public HTTPS URL.
- [ ] Confirm the deployed site displays the Hangman web interface.
- [ ] Confirm the required REST API endpoints work on the deployed URL (e.g. with `curl`).
- [ ] Play a complete game in the browser on the deployed URL.
- [ ] Document the deployment URL, deployment steps, and known limitations (free-tier cold starts, in-memory games reset on restart) in the README.

### Completion Criteria

A user can open the public HTTPS URL and play a complete game in the browser without installing Python or running a local server.

---

## Phase 6 — Documentation

### Tasks

- [ ] Create or update `README.md`.
- [ ] Document project scope and any deviations from the specification.
- [ ] Document installation and how to run the server locally.
- [ ] Document how to use the browser client.
- [ ] Document the REST API with example requests and responses.
- [ ] Document how to run the tests.
- [ ] Document the deployed URL and deployment steps.
- [ ] Verify that a fresh clone works from the documented instructions.

### Completion Criteria

A new user can clone the project, install dependencies, run the tests, start the server, and play in the browser using only the documentation.

---

# Out of Scope

The following parts of the original specification and roadmap are **not** part of this project and should not be implemented:

- Human terminal client (`terminal_client.py`)
- Reference automated clients (`random_bot.py`, `frequency_bot.py`)
- Dictionary-based bot (`dictionary_bot.py`)
- Evaluation mode and evaluation API endpoints
- Official scoring system
- Leaderboard (API and browser view)
- Evaluation integrity and anti-cheating safeguards (rate limiting, idle timeouts, action logs, separate evaluation word lists)
- Logging and replay endpoints and `replay.py`
- Optional future phases: persistent storage, accounts and authentication, tournament mode, advanced bot analysis, multiplayer

---

# Recommended Development Order

1. Game Engine and Word Management
2. Flask Server and REST API
3. Browser Client
4. Testing and Debugging
5. Cloud Deployment
6. Documentation
