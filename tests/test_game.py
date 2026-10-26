"""Unit tests for game.py (Phase 1). No web server is required."""

import pytest

from game import (
    MAX_INCORRECT_GUESSES,
    STATUS_LOST,
    STATUS_PLAYING,
    STATUS_WON,
    DuplicateGuessError,
    GameOverError,
    GuessError,
    HangmanGame,
    InvalidGuessError,
)
from word_manager import InvalidDifficultyError, WordManager


def play(game, letters):
    for letter in letters:
        game.guess(letter)
    return game


# ----- new game ------------------------------------------------------------

def test_new_game_initial_state():
    game = HangmanGame("apple", "easy")
    assert game.status == STATUS_PLAYING
    assert game.pattern == "_ _ _ _ _"
    assert game.remaining_guesses == MAX_INCORRECT_GUESSES == 6
    assert game.guessed_letters == []
    assert game.correct_letters == []
    assert game.incorrect_letters == []
    assert not game.is_over


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
def test_game_can_start_at_every_difficulty(difficulty):
    word = WordManager().random_word(difficulty)
    game = HangmanGame(word, difficulty)
    assert game.difficulty == difficulty
    assert game.status == STATUS_PLAYING
    assert game.pattern == " ".join("_" * len(word))


@pytest.mark.parametrize("bad_word", ["", "ice-cream", "abc1", "two words", None])
def test_invalid_hidden_word_is_rejected(bad_word):
    with pytest.raises(ValueError):
        HangmanGame(bad_word, "easy")


def test_invalid_difficulty_is_rejected():
    with pytest.raises(InvalidDifficultyError):
        HangmanGame("apple", "expert")


def test_hidden_word_is_normalized_to_lowercase():
    game = HangmanGame("  ApPle ", "easy")
    play(game, "aple")
    assert game.to_dict()["word"] == "apple"


# ----- correct and incorrect guesses --------------------------------------

def test_correct_guess_reveals_every_position():
    game = HangmanGame("apple", "easy")
    assert game.guess("p") is True
    assert game.pattern == "_ p p _ _"
    assert game.correct_letters == ["p"]
    assert game.remaining_guesses == 6


def test_incorrect_guess_costs_a_life():
    game = HangmanGame("apple", "easy")
    assert game.guess("z") is False
    assert game.pattern == "_ _ _ _ _"
    assert game.incorrect_letters == ["z"]
    assert game.remaining_guesses == 5


def test_guesses_are_case_insensitive_and_trimmed():
    game = HangmanGame("apple", "easy")
    assert game.guess(" A ") is True
    assert game.guessed_letters == ["a"]
    assert game.pattern == "a _ _ _ _"


def test_guessed_letters_keep_order_and_split_correctly():
    game = play(HangmanGame("apple", "easy"), "zpqe")
    assert game.guessed_letters == ["z", "p", "q", "e"]
    assert game.correct_letters == ["p", "e"]
    assert game.incorrect_letters == ["z", "q"]
    assert game.remaining_guesses == 4


# ----- invalid and duplicate guesses --------------------------------------

@pytest.mark.parametrize("bad", ["", "  ", "ab", "1", "!", "é", None, 5, ["a"]])
def test_invalid_guess_is_rejected_without_changing_state(bad):
    game = HangmanGame("apple", "easy")
    before = game.to_dict()
    with pytest.raises(InvalidGuessError):
        game.guess(bad)
    assert game.to_dict() == before


@pytest.mark.parametrize("repeat", ["p", "P", "z", "Z"])
def test_duplicate_guess_is_rejected_without_changing_state(repeat):
    game = play(HangmanGame("apple", "easy"), "pz")
    before = game.to_dict()
    with pytest.raises(DuplicateGuessError):
        game.guess(repeat)
    assert game.to_dict() == before
    assert game.remaining_guesses == 5  # duplicate wrong guess costs nothing


def test_all_guess_errors_share_a_base_class():
    assert issubclass(InvalidGuessError, GuessError)
    assert issubclass(DuplicateGuessError, GuessError)
    assert issubclass(GameOverError, GuessError)


# ----- winning and losing --------------------------------------------------

def test_win_when_all_letters_found():
    game = play(HangmanGame("apple", "easy"), "aple")
    assert game.status == STATUS_WON
    assert game.is_over
    assert game.pattern == "a p p l e"


def test_win_with_some_wrong_guesses():
    game = play(HangmanGame("cat", "easy"), "xyzcat")
    assert game.status == STATUS_WON
    assert game.remaining_guesses == 3


def test_win_on_last_letter_with_one_life_left():
    game = play(HangmanGame("cat", "easy"), "uvwxyca")
    assert game.remaining_guesses == 1
    assert game.status == STATUS_PLAYING
    game.guess("t")
    assert game.status == STATUS_WON


def test_loss_after_six_wrong_guesses():
    game = HangmanGame("apple", "easy")
    play(game, "qrstu")
    assert game.status == STATUS_PLAYING
    assert game.remaining_guesses == 1
    game.guess("v")
    assert game.status == STATUS_LOST
    assert game.remaining_guesses == 0
    assert game.is_over


def test_custom_max_incorrect():
    game = play(HangmanGame("apple", "easy", max_incorrect=2), "qr")
    assert game.status == STATUS_LOST


# ----- no guesses after the game ends --------------------------------------

@pytest.mark.parametrize("letters", ["aple", "qrstuv"])
def test_no_guesses_after_game_ends(letters):
    game = play(HangmanGame("apple", "easy"), letters)
    before = game.to_dict()
    for attempt in ["b", "a", "!", ""]:
        with pytest.raises(GameOverError):
            game.guess(attempt)
    assert game.to_dict() == before


# ----- client-safe state and answer disclosure -----------------------------

def test_to_dict_fields_while_playing():
    game = play(HangmanGame("apple", "easy"), "pz")
    assert game.to_dict() == {
        "difficulty": "easy",
        "pattern": "_ p p _ _",
        "word_length": 5,
        "guessed_letters": ["p", "z"],
        "correct_letters": ["p"],
        "incorrect_letters": ["z"],
        "remaining_guesses": 5,
        "max_incorrect": 6,
        "status": "playing",
    }


def test_word_is_never_in_state_while_playing():
    game = HangmanGame("rhythm", "hard")
    for letter in "rhytaeiou":
        state = game.to_dict()
        if state["status"] != STATUS_PLAYING:
            break
        assert "word" not in state
        assert "rhythm" not in repr(state)
        game.guess(letter)


def test_word_revealed_after_win():
    game = play(HangmanGame("apple", "easy"), "aple")
    assert game.to_dict()["word"] == "apple"


def test_word_revealed_after_loss():
    game = play(HangmanGame("apple", "easy"), "qrstuv")
    state = game.to_dict()
    assert state["status"] == STATUS_LOST
    assert state["word"] == "apple"
    assert state["pattern"] == "_ _ _ _ _"  # pattern stays masked


def test_to_dict_returns_copies():
    game = play(HangmanGame("apple", "easy"), "p")
    state = game.to_dict()
    state["guessed_letters"].append("x")
    assert game.guessed_letters == ["p"]


# ----- separate games -------------------------------------------------------

def test_games_do_not_share_state():
    first = HangmanGame("apple", "easy")
    second = HangmanGame("apple", "easy")
    first.guess("a")
    assert second.guessed_letters == []
