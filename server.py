"""Flask server and REST API for Hangman.

Endpoints
---------
POST /api/games                   Create a new game.
GET  /api/games/<game_id>         Retrieve the current game state.
POST /api/games/<game_id>/guess   Submit a letter guess.
GET  /                            Serve the browser client.

All API requests and responses use JSON. The server is authoritative:
every guess is checked by ``HangmanGame`` here, and the hidden word is
only included in a response after the game has ended.

Run locally:
    python server.py            # http://127.0.0.1:5000
"""

from __future__ import annotations

import secrets
import threading
from collections import OrderedDict
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from game import DuplicateGuessError, GameOverError, HangmanGame, InvalidGuessError
from word_manager import InvalidDifficultyError, WordManager, normalize_difficulty

DEFAULT_DIFFICULTY = "medium"
MAX_STORED_GAMES = 10_000  # oldest games are dropped beyond this, so memory stays bounded
MAX_REQUEST_BYTES = 16 * 1024  # real requests are ~30 bytes; larger bodies get HTTP 413

STATIC_DIR = Path(__file__).resolve().parent / "static"


def error_response(message: str, status: int):
    """Return a consistent JSON error body: {"error": "..."}."""
    return jsonify({"error": message}), status


class GameStore:
    """Thread-safe in-memory storage for active games."""

    def __init__(self, max_games: int = MAX_STORED_GAMES) -> None:
        self._games: OrderedDict[str, HangmanGame] = OrderedDict()
        self._lock = threading.Lock()
        self.max_games = max_games

    def add(self, game: HangmanGame) -> str:
        with self._lock:
            game_id = secrets.token_hex(8)  # 16 random hex characters
            while game_id in self._games:
                game_id = secrets.token_hex(8)
            self._games[game_id] = game
            while len(self._games) > self.max_games:
                self._games.popitem(last=False)
            return game_id

    def get(self, game_id: str) -> HangmanGame | None:
        with self._lock:
            return self._games.get(game_id)

    @property
    def lock(self) -> threading.Lock:
        return self._lock

    def __len__(self) -> int:
        return len(self._games)


def game_response(game_id: str, game: HangmanGame, **extra) -> dict:
    """The JSON body sent for a game: its id plus the engine's client-safe state."""
    return {"game_id": game_id, **game.to_dict(), **extra}


def read_json_object():
    """Return the request body as a dict, or None if it isn't a JSON object."""
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else None


def create_app(word_manager: WordManager | None = None) -> Flask:
    """Build the Flask app. Tests pass their own WordManager."""
    app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")
    app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES
    words = word_manager or WordManager()
    store = GameStore()
    app.config["GAME_STORE"] = store

    # ----- browser client ------------------------------------------------

    @app.get("/")
    def index():
        return send_from_directory(STATIC_DIR, "index.html")

    # ----- REST API ------------------------------------------------------

    @app.post("/api/games")
    def create_game():
        body = read_json_object()
        if body is None:
            return error_response(
                'Request body must be a JSON object, e.g. {"difficulty": "medium"}.', 400
            )
        try:
            difficulty = normalize_difficulty(body.get("difficulty", DEFAULT_DIFFICULTY))
        except InvalidDifficultyError as error:
            return error_response(str(error), 400)

        game = HangmanGame(words.random_word(difficulty), difficulty)
        game_id = store.add(game)
        return jsonify(game_response(game_id, game)), 201

    @app.get("/api/games/<game_id>")
    def get_game(game_id: str):
        game = store.get(game_id)
        if game is None:
            return error_response(f"Game {game_id!r} not found.", 404)
        with store.lock:
            return jsonify(game_response(game_id, game)), 200

    @app.post("/api/games/<game_id>/guess")
    def guess(game_id: str):
        game = store.get(game_id)
        if game is None:
            return error_response(f"Game {game_id!r} not found.", 404)

        body = read_json_object()
        if body is None:
            return error_response(
                'Request body must be a JSON object, e.g. {"letter": "e"}.', 400
            )
        if "letter" not in body:
            return error_response('Missing required field "letter".', 400)

        with store.lock:  # one guess at a time, so state can't race
            try:
                correct = game.guess(body["letter"])
            except InvalidGuessError as error:
                return error_response(str(error), 400)
            except (DuplicateGuessError, GameOverError) as error:
                return error_response(str(error), 409)
            return jsonify(game_response(game_id, game, correct=correct)), 200

    # ----- JSON errors for everything else -------------------------------

    @app.errorhandler(413)
    def too_large(error):
        return error_response(
            f"Request body is too large (limit {MAX_REQUEST_BYTES} bytes).", 413
        )

    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException):
        return error_response(error.description or error.name, error.code or 500)

    @app.errorhandler(Exception)
    def unexpected_error(error: Exception):
        app.logger.exception("Unhandled error")
        return error_response("Internal server error.", 500)

    return app


app = create_app()


if __name__ == "__main__":
    # Local development only. In production Gunicorn imports `app` directly
    # and this block never runs, so debug mode is never on in the cloud.
    app.run(host="127.0.0.1", port=5000, debug=True)
