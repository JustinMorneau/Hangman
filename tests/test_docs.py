"""Phase 6: checks that README.md matches what the code really does.

If the API or project layout changes, these fail until the docs are updated.
"""

import json
import re
from pathlib import Path

import pytest

from server import create_app
from word_manager import WordManager

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")


@pytest.fixture
def client(tmp_path):
    for difficulty, word in {"easy": "apple", "medium": "garden", "hard": "rhythm"}.items():
        (tmp_path / f"{difficulty}.txt").write_text(word + "\n", encoding="utf-8")
    return create_app(WordManager(tmp_path)).test_client()


def json_examples():
    return [json.loads(block) for block in re.findall(r"```json\n(.*?)```", README, re.S)]


def real_state_key_sets(client):
    """Every set of keys a real successful response can have."""
    created = client.post("/api/games", json={"difficulty": "easy"}).get_json()
    game_id = created["game_id"]
    guessed = client.post(f"/api/games/{game_id}/guess", json={"letter": "p"}).get_json()
    for letter in "ale":
        finished = client.post(f"/api/games/{game_id}/guess", json={"letter": letter}).get_json()
    fetched = client.get(f"/api/games/{game_id}").get_json()
    return {frozenset(s) for s in (created, guessed, finished, fetched)}


def test_readme_json_examples_are_valid_json():
    assert len(json_examples()) >= 4


def test_readme_state_examples_match_real_responses(client):
    valid = real_state_key_sets(client)
    states = [e for e in json_examples() if "status" in e]
    assert states, "README has no game-state examples"
    for example in states:
        assert frozenset(example) in valid, f"README example has wrong fields: {sorted(example)}"
        if example["status"] == "playing":
            assert "word" not in example


def test_readme_error_examples_have_one_field():
    errors = [e for e in json_examples() if "error" in e]
    assert errors and all(set(e) == {"error"} for e in errors)


def test_every_field_in_responses_is_documented(client):
    fields = set().union(*real_state_key_sets(client))
    for field in fields:
        assert f"| `{field}` |" in README, f"field {field!r} missing from the README table"


def test_readme_error_messages_match_server(client):
    game_id = client.post("/api/games", json={"difficulty": "easy"}).get_json()["game_id"]
    guess = f"/api/games/{game_id}/guess"
    client.post(guess, json={"letter": "e"})
    responses = {
        400: [
            client.post("/api/games"),
            client.post("/api/games", json={"difficulty": "expert"}),
            client.post(guess, json={}),
            client.post(guess, json={"letter": "ab"}),
        ],
        404: [client.get("/api/games/abc123")],
        405: [client.delete("/api/games")],
        409: [client.post(guess, json={"letter": "e"})],
        413: [client.post("/api/games", json={"pad": "x" * 20_000})],
    }
    for status, items in responses.items():
        for response in items:
            assert response.status_code == status
            message = response.get_json()["error"]
            assert message in README, f"{status} message not in README: {message!r}"
            assert f"| `{status}` |" in README


def test_readme_documents_every_endpoint():
    for method, endpoint in [
        ("POST", "/api/games"),
        ("GET", "/api/games/{game_id}"),
        ("POST", "/api/games/{game_id}/guess"),
    ]:
        assert f"| `{method}` | `{endpoint}` |" in README


def test_files_listed_in_readme_exist():
    table = README.split("### Project files", 1)[1].split("\n## ", 1)[0]
    first_cells = re.findall(r"^\| ([^|]+) \|", table, re.M)
    names = [n for cell in first_cells for n in re.findall(r"`([^`]+)`", cell)]
    assert len(names) >= 10
    for name in names:
        assert (ROOT / name).exists(), f"README lists {name!r}, which does not exist"


def test_readme_links_to_live_app():
    assert "https://hangman-fo4n.onrender.com" in README
    assert "YOUR-APP" not in README
