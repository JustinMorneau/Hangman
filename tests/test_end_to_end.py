"""Phase 4: end-to-end tests that play complete games through the REST API.

1. Many full games against the REAL word lists, checking that every
   response obeys the game rules at every step.
2. A full game over real HTTP (like curl or the browser) against a live server.
3. Simultaneous requests to one game, to show the server's lock keeps the
   state consistent.
"""

import json
import threading
import urllib.error
import urllib.request

import pytest

from conftest import KNOWN_WORDS
from server import create_app

# Common English letters first, so most games are won and some are lost.
GUESS_ORDER = "etaoinshrdlcumwfgypbvkjxqz"


def check_invariants(state, game_id, difficulty):
    """Rules every response must follow, at every step of every game."""
    assert state["game_id"] == game_id
    assert state["difficulty"] == difficulty
    assert state["status"] in ("playing", "won", "lost")
    assert state["remaining_guesses"] == 6 - len(state["incorrect_letters"])
    assert 0 <= state["remaining_guesses"] <= 6
    assert sorted(state["guessed_letters"]) == sorted(
        state["correct_letters"] + state["incorrect_letters"]
    )
    assert len(set(state["guessed_letters"])) == len(state["guessed_letters"])
    shown = state["pattern"].split(" ")
    assert len(shown) == state["word_length"]
    assert all(c == "_" or c in state["correct_letters"] for c in shown)

    if state["status"] == "playing":
        assert "word" not in state
        assert state["remaining_guesses"] > 0 and "_" in shown
    else:
        word = state["word"]
        assert len(word) == state["word_length"]
        # every revealed letter matches the real word
        assert all(c == "_" or c == w for c, w in zip(shown, word))
        if state["status"] == "won":
            assert "_" not in shown
        else:
            assert state["remaining_guesses"] == 0


def play_full_game(client, difficulty):
    created = client.post("/api/games", json={"difficulty": difficulty})
    assert created.status_code == 201
    state = created.get_json()
    game_id = state["game_id"]
    check_invariants(state, game_id, difficulty)

    for letter in GUESS_ORDER:
        if state["status"] != "playing":
            break
        response = client.post(f"/api/games/{game_id}/guess", json={"letter": letter})
        assert response.status_code == 200
        state = response.get_json()
        check_invariants(state, game_id, difficulty)
        assert state == {**client.get(f"/api/games/{game_id}").get_json(),
                         "correct": state["correct"]}

    assert state["status"] in ("won", "lost")
    after = client.post(f"/api/games/{game_id}/guess", json={"letter": "a"})
    assert after.status_code == 409  # finished games accept no more guesses
    return state


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
def test_many_full_games_with_real_word_lists(difficulty):
    client = create_app().test_client()
    outcomes = [play_full_game(client, difficulty)["status"] for _ in range(40)]
    assert set(outcomes) <= {"won", "lost"}
    assert len(outcomes) == 40


# ----- over real HTTP -----------------------------------------------------------

def http(base, method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        base + path, data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def test_full_game_over_http(live_server):
    base = live_server["url"]
    status, game = http(base, "POST", "/api/games", {"difficulty": "easy"})
    assert status == 201 and game["pattern"] == "_ _ _ _ _"
    game_id = game["game_id"]

    status, state = http(base, "POST", f"/api/games/{game_id}/guess", {"letter": "z"})
    assert status == 200 and state["remaining_guesses"] == 5

    for letter in "aple":
        status, state = http(base, "POST", f"/api/games/{game_id}/guess", {"letter": letter})
        assert status == 200
    assert state["status"] == "won" and state["word"] == KNOWN_WORDS["easy"]

    status, state = http(base, "GET", f"/api/games/{game_id}")
    assert status == 200 and state["status"] == "won"

    status, error = http(base, "POST", f"/api/games/{game_id}/guess", {"letter": "b"})
    assert status == 409 and "error" in error


# ----- simultaneous requests ----------------------------------------------------

def run_together(calls):
    results = [None] * len(calls)

    def worker(index, call):
        results[index] = call()

    threads = [threading.Thread(target=worker, args=(i, c)) for i, c in enumerate(calls)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return results


def test_same_letter_at_once_is_accepted_exactly_once(live_server):
    base = live_server["url"]
    for _ in range(10):
        game_id = http(base, "POST", "/api/games", {"difficulty": "hard"})[1]["game_id"]
        path = f"/api/games/{game_id}/guess"
        results = run_together([lambda: http(base, "POST", path, {"letter": "e"})] * 15)
        codes = sorted(code for code, _ in results)
        assert codes == [200] + [409] * 14


def test_different_letters_at_once_keep_state_consistent(live_server):
    base = live_server["url"]
    game_id = http(base, "POST", "/api/games", {"difficulty": "hard"})[1]["game_id"]
    path = f"/api/games/{game_id}/guess"
    letters = "bcdfhijklmopqsuw"  # 16 letters, none in "extravaganza"
    results = run_together(
        [lambda l=letter: http(base, "POST", path, {"letter": l}) for letter in letters]
    )
    accepted = [code for code, _ in results if code == 200]
    assert len(accepted) == 6                      # the 6th miss ends the game
    _, state = http(base, "GET", f"/api/games/{game_id}")
    assert state["status"] == "lost"
    assert len(state["incorrect_letters"]) == 6    # never more than 6
    assert state["remaining_guesses"] == 0
