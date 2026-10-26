"""Shared pytest fixtures.

``live_server`` runs the real Flask app on a free local port in a background
thread (multi-threaded, like a real deployment can be). Each difficulty has
one known word so games are predictable:

    easy = apple, medium = garden, hard = extravaganza (12 letters,
    the longest word the layout is tested with)
"""

import logging
import threading

import pytest
from werkzeug.serving import make_server

from server import create_app
from word_manager import WordManager

KNOWN_WORDS = {"easy": "apple", "medium": "garden", "hard": "extravaganza"}


@pytest.fixture(scope="module")
def live_server(tmp_path_factory):
    words = tmp_path_factory.mktemp("words")
    for difficulty, word in KNOWN_WORDS.items():
        (words / f"{difficulty}.txt").write_text(word + "\n", encoding="utf-8")

    app = create_app(WordManager(words))
    logging.getLogger("werkzeug").setLevel(logging.ERROR)  # hide per-request log lines
    server = make_server("127.0.0.1", 0, app, threaded=True)  # port 0 = any free port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield {"url": f"http://127.0.0.1:{server.server_port}", "app": app}
    server.shutdown()
