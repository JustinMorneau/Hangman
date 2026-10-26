"""API tests for server.py (Phase 2). Uses Flask's test client; no real server runs."""

import json

import pytest

from server import create_app
from word_manager import WordManager


@pytest.fixture
def words_dir(tmp_path):
    """One known word per difficulty, so tests can play games deterministically."""
    (tmp_path / "easy.txt").write_text("apple\n", encoding="utf-8")
    (tmp_path / "medium.txt").write_text("garden\n", encoding="utf-8")
    (tmp_path / "hard.txt").write_text("rhythm\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def client(words_dir):
    app = create_app(WordManager(words_dir))
    app.config["TESTING"] = True
    return app.test_client()


def new_game(client, difficulty="easy"):
    response = client.post("/api/games", json={"difficulty": difficulty})
    assert response.status_code == 201
    return response.get_json()


def guess(client, game_id, letter):
    return client.post(f"/api/games/{game_id}/guess", json={"letter": letter})


def play(client, game_id, letters):
    for letter in letters:
        response = guess(client, game_id, letter)
        assert response.status_code == 200, response.get_json()
    return response.get_json()


# ----- creating games -------------------------------------------------------

@pytest.mark.parametrize(
    "difficulty, length", [("easy", 5), ("medium", 6), ("hard", 6)]
)
def test_create_game_at_every_difficulty(client, difficulty, length):
    data = new_game(client, difficulty)
    assert data["difficulty"] == difficulty
    assert data["status"] == "playing"
    assert data["remaining_guesses"] == 6
    assert data["pattern"] == " ".join("_" * length)
    assert data["guessed_letters"] == []
    assert isinstance(data["game_id"], str) and data["game_id"]


def test_create_game_with_real_word_lists():
    client = create_app().test_client()
    for difficulty in ("easy", "medium", "hard"):
        response = client.post("/api/games", json={"difficulty": difficulty})
        assert response.status_code == 201
        assert "word" not in response.get_json()


def test_difficulty_is_case_insensitive(client):
    assert new_game(client, "HARD")["difficulty"] == "hard"


def test_difficulty_defaults_to_medium(client):
    response = client.post("/api/games", json={})
    assert response.status_code == 201
    assert response.get_json()["difficulty"] == "medium"


def test_response_is_json(client):
    response = client.post("/api/games", json={"difficulty": "easy"})
    assert response.is_json


def test_game_ids_are_unique(client):
    ids = {new_game(client)["game_id"] for _ in range(50)}
    assert len(ids) == 50


@pytest.mark.parametrize("bad", ["expert", "", None, 3, ["easy"]])
def test_invalid_difficulty_returns_400(client, bad):
    response = client.post("/api/games", json={"difficulty": bad})
    assert response.status_code == 400
    assert "error" in response.get_json()


@pytest.mark.parametrize(
    "kwargs",
    [
        {},                                                          # no body
        {"data": "not json", "content_type": "application/json"},    # malformed JSON
        {"data": '{"difficulty": "easy"}', "content_type": "text/plain"},  # wrong type
        {"json": ["easy"]},                                          # JSON but not an object
        {"json": "easy"},
    ],
)
def test_malformed_create_request_returns_400(client, kwargs):
    response = client.post("/api/games", **kwargs)
    assert response.status_code == 400
    assert response.is_json and "error" in response.get_json()


# ----- retrieving games -----------------------------------------------------

def test_get_game_returns_current_state(client):
    game_id = new_game(client)["game_id"]
    guess(client, game_id, "p")
    response = client.get(f"/api/games/{game_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["game_id"] == game_id
    assert data["pattern"] == "_ p p _ _"
    assert data["guessed_letters"] == ["p"]


def test_unknown_game_returns_404(client):
    assert client.get("/api/games/doesnotexist").status_code == 404
    response = guess(client, "doesnotexist", "a")
    assert response.status_code == 404
    assert "error" in response.get_json()


# ----- guessing -------------------------------------------------------------

def test_correct_guess(client):
    game_id = new_game(client)["game_id"]
    response = guess(client, game_id, "p")
    assert response.status_code == 200
    data = response.get_json()
    assert data["correct"] is True
    assert data["pattern"] == "_ p p _ _"
    assert data["correct_letters"] == ["p"]
    assert data["remaining_guesses"] == 6


def test_incorrect_guess(client):
    game_id = new_game(client)["game_id"]
    data = guess(client, game_id, "z").get_json()
    assert data["correct"] is False
    assert data["incorrect_letters"] == ["z"]
    assert data["remaining_guesses"] == 5


def test_uppercase_guess_is_accepted(client):
    game_id = new_game(client)["game_id"]
    data = guess(client, game_id, "A").get_json()
    assert data["correct"] is True
    assert data["guessed_letters"] == ["a"]


@pytest.mark.parametrize("bad", ["", "ab", "1", "!", "é", None, 7, ["a"]])
def test_invalid_letter_returns_400_and_changes_nothing(client, bad):
    game_id = new_game(client)["game_id"]
    response = guess(client, game_id, bad)
    assert response.status_code == 400
    state = client.get(f"/api/games/{game_id}").get_json()
    assert state["guessed_letters"] == []
    assert state["remaining_guesses"] == 6


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"json": {}},
        {"json": {"guess": "a"}},
        {"json": ["a"]},
        {"data": "letter=a", "content_type": "application/x-www-form-urlencoded"},
        {"data": "{bad json", "content_type": "application/json"},
    ],
)
def test_malformed_guess_request_returns_400(client, kwargs):
    game_id = new_game(client)["game_id"]
    response = client.post(f"/api/games/{game_id}/guess", **kwargs)
    assert response.status_code == 400
    assert "error" in response.get_json()


@pytest.mark.parametrize("repeat", ["p", "P", "z"])
def test_duplicate_guess_returns_409_and_changes_nothing(client, repeat):
    game_id = new_game(client)["game_id"]
    play(client, game_id, "pz")
    response = guess(client, game_id, repeat)
    assert response.status_code == 409
    state = client.get(f"/api/games/{game_id}").get_json()
    assert state["guessed_letters"] == ["p", "z"]
    assert state["remaining_guesses"] == 5


# ----- winning, losing, and finished games ----------------------------------

def test_win_through_api(client):
    game_id = new_game(client)["game_id"]
    data = play(client, game_id, "aple")
    assert data["status"] == "won"
    assert data["pattern"] == "a p p l e"
    assert data["word"] == "apple"


def test_loss_through_api(client):
    game_id = new_game(client)["game_id"]
    data = play(client, game_id, "qrstuv")
    assert data["status"] == "lost"
    assert data["remaining_guesses"] == 0
    assert data["word"] == "apple"


@pytest.mark.parametrize("letters", ["aple", "qrstuv"])
def test_guess_after_game_over_returns_409(client, letters):
    game_id = new_game(client)["game_id"]
    play(client, game_id, letters)
    response = guess(client, game_id, "b")
    assert response.status_code == 409
    assert "error" in response.get_json()


def test_new_game_after_finishing_one(client):
    first = new_game(client)["game_id"]
    play(client, first, "aple")
    second = new_game(client, "medium")
    assert second["game_id"] != first
    assert second["status"] == "playing"
    assert second["guessed_letters"] == []
    # the finished game is still readable and unchanged
    assert client.get(f"/api/games/{first}").get_json()["status"] == "won"


# ----- separate game states -------------------------------------------------

def test_games_keep_separate_state(client):
    a = new_game(client)["game_id"]
    b = new_game(client)["game_id"]
    guess(client, a, "p")
    guess(client, b, "z")
    state_a = client.get(f"/api/games/{a}").get_json()
    state_b = client.get(f"/api/games/{b}").get_json()
    assert state_a["guessed_letters"] == ["p"]
    assert state_b["guessed_letters"] == ["z"]
    assert state_b["remaining_guesses"] == 5


# ----- hidden word never leaks during play ----------------------------------

@pytest.mark.parametrize("difficulty, word", [("easy", "apple"), ("medium", "garden"), ("hard", "rhythm")])
def test_word_never_in_any_response_while_playing(client, difficulty, word):
    created = client.post("/api/games", json={"difficulty": difficulty})
    game_id = created.get_json()["game_id"]
    responses = [created, client.get(f"/api/games/{game_id}")]
    for letter in "xyzqj":  # wrong guesses, game keeps going (rhythm has y; still playing)
        responses.append(guess(client, game_id, letter))
        responses.append(client.get(f"/api/games/{game_id}"))
    for response in responses:
        data = response.get_json()
        if data.get("status") == "playing":
            assert "word" not in data
            assert word not in response.get_data(as_text=True)


# ----- other routes ---------------------------------------------------------

def test_unknown_api_route_returns_json_404(client):
    response = client.get("/api/nope")
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_wrong_method_returns_json_405(client):
    response = client.delete("/api/games")
    assert response.status_code == 405
    assert "error" in response.get_json()


def test_index_page_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Hangman" in response.data
