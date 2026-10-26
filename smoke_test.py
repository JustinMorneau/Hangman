"""Smoke test for a running Hangman server, local or deployed.

Plays complete games through the public REST API, the same way the browser
does, and checks the deployment requirements. Uses only the standard library.

Usage:
    python smoke_test.py http://127.0.0.1:5000
    python smoke_test.py https://your-app.onrender.com

Exit code 0 means every check passed.

Free Render services sleep when idle, so the first request can take up to
about a minute while the server wakes up. That is expected.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

TIMEOUT_SECONDS = 90  # long enough for a free-tier cold start
GUESS_ORDER = "etaoinshrdlcumwfgypbvkjxqz"


class SmokeTest:
    def __init__(self, base_url: str) -> None:
        self.base = base_url.rstrip("/")
        self.failures: list[str] = []

    # ----- HTTP helpers --------------------------------------------------

    def request(self, method: str, path: str, body: dict | None = None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(
            self.base + path, data=data, method=method,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
                raw = response.read().decode("utf-8")
                return response.status, response.headers.get_content_type(), raw
        except urllib.error.HTTPError as error:
            raw = error.read().decode("utf-8")
            return error.code, error.headers.get_content_type(), raw

    def api(self, method: str, path: str, body: dict | None = None):
        status, content_type, raw = self.request(method, path, body)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = None
        if content_type != "application/json" or data is None:
            self.check(False, f"{method} {path} returns JSON (got {content_type})")
        return status, data, raw

    def check(self, condition: bool, description: str) -> bool:
        print(("  PASS  " if condition else "  FAIL  ") + description)
        if not condition:
            self.failures.append(description)
        return condition

    # ----- checks ----------------------------------------------------------

    def run(self) -> bool:
        print(f"Smoke testing {self.base}\n")
        self.check_transport()
        self.check_web_interface()
        for difficulty in ("easy", "medium", "hard"):
            self.play_full_game(difficulty)
        self.check_errors()
        self.check_new_game_after_finished()

        print()
        if self.failures:
            print(f"{len(self.failures)} check(s) FAILED:")
            for failure in self.failures:
                print(f"  - {failure}")
            return False
        print("All checks passed.")
        return True

    def check_transport(self) -> None:
        print("Connection")
        host = urlparse(self.base).hostname or ""
        local = host in ("localhost", "127.0.0.1", "::1")
        if local:
            print("  INFO  local server; the HTTPS check applies to the deployed URL")
        else:
            self.check(self.base.startswith("https://"), "public URL uses HTTPS")

    def check_web_interface(self) -> None:
        print("Web interface")
        started = time.monotonic()
        status, content_type, html = self.request("GET", "/")
        elapsed = time.monotonic() - started
        if elapsed > 5:
            print(f"  INFO  first response took {elapsed:.0f}s (server was probably asleep)")
        self.check(status == 200 and content_type == "text/html", "GET / serves the page")
        self.check("Hangman" in html and 'id="keyboard"' in html,
                   "page contains the Hangman interface")
        for path in ("/static/app.js", "/static/style.css"):
            status, _, _ = self.request("GET", path)
            self.check(status == 200, f"GET {path} is served")

    def play_full_game(self, difficulty: str) -> None:
        print(f"Full game ({difficulty})")
        status, state, raw = self.api("POST", "/api/games", {"difficulty": difficulty})
        if not self.check(status == 201 and state, f"POST /api/games creates a game ({difficulty})"):
            return
        game_id = state["game_id"]
        self.check(state["status"] == "playing" and "word" not in state,
                   "new game is playing and hides the word")

        status, fetched, _ = self.api("GET", f"/api/games/{game_id}")
        self.check(status == 200 and bool(fetched) and fetched.get("game_id") == game_id,
                   "GET /api/games/{id} returns the game")

        leaked = False
        for letter in GUESS_ORDER:
            if state["status"] != "playing":
                break
            status, state, raw = self.api(
                "POST", f"/api/games/{game_id}/guess", {"letter": letter}
            )
            if status != 200:
                self.check(False, f"guess {letter!r} accepted (got HTTP {status})")
                return
            if state["status"] == "playing" and ("word" in state or '"word"' in raw):
                leaked = True

        self.check(not leaked, "word never sent while the game is playing")
        finished = state["status"] in ("won", "lost") and "word" in state
        if self.check(finished, "game finishes and reveals the word"):
            print(f"  INFO  {state['status']} with {state['remaining_guesses']} "
                  f"guesses left; word was {state['word']!r}")

        status, _, _ = self.api("POST", f"/api/games/{game_id}/guess", {"letter": "a"})
        self.check(status == 409, "guess after the game ends is rejected (409)")

    def check_errors(self) -> None:
        print("Invalid requests")
        status, data, _ = self.api("POST", "/api/games", {"difficulty": "impossible"})
        self.check(status == 400 and "error" in (data or {}), "invalid difficulty gives 400")

        status, _, _ = self.api("GET", "/api/games/no-such-game")
        self.check(status == 404, "unknown game id gives 404")

        status, game, _ = self.api("POST", "/api/games", {"difficulty": "easy"})
        if status != 201:
            return
        path = f"/api/games/{game['game_id']}/guess"
        status, _, _ = self.api("POST", path, {"letter": "ab"})
        self.check(status == 400, "two-letter guess gives 400")
        status, _, _ = self.api("POST", path, {})
        self.check(status == 400, "missing letter gives 400")
        self.api("POST", path, {"letter": "e"})
        status, _, _ = self.api("POST", path, {"letter": "e"})
        self.check(status == 409, "duplicate guess gives 409")

    def check_new_game_after_finished(self) -> None:
        print("Separate games")
        _, first, _ = self.api("POST", "/api/games", {"difficulty": "easy"})
        _, second, _ = self.api("POST", "/api/games", {"difficulty": "easy"})
        if not (first and second):
            self.check(False, "two games can be created")
            return
        self.check(first["game_id"] != second["game_id"], "each game gets a unique id")
        self.api("POST", f"/api/games/{first['game_id']}/guess", {"letter": "e"})
        _, other, _ = self.api("GET", f"/api/games/{second['game_id']}")
        self.check(bool(other) and other.get("guessed_letters") == [], "a guess in one game does not affect another")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    try:
        ok = SmokeTest(argv[1]).run()
    except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
        print(f"\nCould not reach the server: {error}")
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
