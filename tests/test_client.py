"""Phase 3: checks that the browser client is served and contains no game logic.

These run with plain pytest (no browser needed). The full in-browser tests
are in test_browser.py.
"""

import re
from pathlib import Path

import pytest

from server import create_app
from word_manager import WordManager

STATIC = Path(__file__).resolve().parent.parent / "static"


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_index_contains_required_controls(client):
    html = client.get("/").get_data(as_text=True)
    for element_id in ["controls", "new-game", "drawing", "pattern", "remaining",
                       "guessed", "misses", "message", "keyboard"]:
        assert f'id="{element_id}"' in html, element_id
    for difficulty in ["easy", "medium", "hard"]:
        assert f'value="{difficulty}"' in html
    assert '/static/app.js' in html and '/static/style.css' in html


def test_drawing_has_six_parts(client):
    html = client.get("/").get_data(as_text=True)
    parts = re.findall(r'data-part="(\d)"', html)
    assert parts == ["1", "2", "3", "4", "5", "6"]


@pytest.mark.parametrize("path, mimetype", [
    ("/static/app.js", "javascript"),
    ("/static/style.css", "text/css"),
])
def test_static_files_are_served(client, path, mimetype):
    response = client.get(path)
    assert response.status_code == 200
    assert mimetype in response.mimetype
    response.close()


def test_client_talks_to_the_rest_api():
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    assert "fetch(" in js
    assert '"/api/games"' in js
    assert "/guess" in js


def test_client_does_not_embed_word_lists():
    """No medium or hard word appears in the JavaScript, and it never loads words/*.txt.

    (Easy words such as "light" or "table" are ordinary English that could
    legitimately appear in code, so they are not checked.)
    """
    js = (STATIC / "app.js").read_text(encoding="utf-8").lower()
    assert "words/" not in js and ".txt" not in js
    tokens = set(re.findall(r"[a-z]+", js))
    manager = WordManager()
    leaked = tokens & (set(manager.get_words("medium")) | set(manager.get_words("hard")))
    assert not leaked, f"word-list words found in app.js: {sorted(leaked)}"


def test_client_does_not_decide_guess_results():
    """The client reads results from the server instead of comparing letters to a word."""
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    assert "game.status" in js and "game.pattern" in js
    assert not re.search(r"word\.(includes|indexOf)\(", js)
