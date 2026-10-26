"""Unit tests for word_manager.py (Phase 1)."""

import random

import pytest

from word_manager import (
    DIFFICULTIES,
    InvalidDifficultyError,
    WordListError,
    WordManager,
    load_word_file,
    normalize_difficulty,
)


def write_lists(directory, easy="cat\n", medium="garden\n", hard="rhythm\n"):
    """Create a complete set of word list files in ``directory``."""
    (directory / "easy.txt").write_text(easy, encoding="utf-8")
    (directory / "medium.txt").write_text(medium, encoding="utf-8")
    (directory / "hard.txt").write_text(hard, encoding="utf-8")
    return directory


# ----- the real word lists shipped in words/ ------------------------------

def test_real_word_lists_load_for_every_difficulty():
    manager = WordManager()
    for difficulty in DIFFICULTIES:
        words = manager.get_words(difficulty)
        assert len(words) > 0


def test_real_word_lists_are_clean():
    manager = WordManager()
    for difficulty in DIFFICULTIES:
        words = manager.get_words(difficulty)
        assert len(words) == len(set(words)), f"duplicates in {difficulty}"
        for word in words:
            assert word.isascii() and word.isalpha() and word.islower(), word


def test_random_word_comes_from_requested_list():
    manager = WordManager()
    for difficulty in DIFFICULTIES:
        for _ in range(20):
            assert manager.random_word(difficulty) in manager.get_words(difficulty)


# ----- loading and validation --------------------------------------------

def test_load_skips_blank_lines_and_comments(tmp_path):
    path = tmp_path / "words.txt"
    path.write_text("# a comment\n\napple\n   \nbanana\n", encoding="utf-8")
    assert load_word_file(path) == ["apple", "banana"]


def test_load_normalizes_case_and_whitespace(tmp_path):
    path = tmp_path / "words.txt"
    path.write_text("  Apple  \nBANANA\n", encoding="utf-8")
    assert load_word_file(path) == ["apple", "banana"]


def test_load_removes_duplicates_keeping_first(tmp_path):
    path = tmp_path / "words.txt"
    path.write_text("apple\nbanana\nApple\napple\ncherry\n", encoding="utf-8")
    assert load_word_file(path) == ["apple", "banana", "cherry"]


@pytest.mark.parametrize("bad_word", ["ice-cream", "two words", "abc123", "café", "don't"])
def test_load_rejects_non_alphabetic_words(tmp_path, bad_word):
    path = tmp_path / "words.txt"
    path.write_text(f"apple\n{bad_word}\n", encoding="utf-8")
    with pytest.raises(WordListError, match="line 2"):
        load_word_file(path)


def test_load_rejects_file_that_is_not_utf8(tmp_path):
    path = tmp_path / "words.txt"
    path.write_bytes("apple\ncaf\u00e9\n".encode("cp1252"))  # é saved as byte 0xE9
    with pytest.raises(WordListError, match="UTF-8"):
        load_word_file(path)


def test_load_accepts_utf8_with_byte_order_mark(tmp_path):
    path = tmp_path / "words.txt"
    path.write_text("apple\nbanana\n", encoding="utf-8-sig")  # as Notepad may save it
    assert load_word_file(path) == ["apple", "banana"]


def test_load_rejects_empty_file(tmp_path):
    path = tmp_path / "words.txt"
    path.write_text("# only a comment\n\n", encoding="utf-8")
    with pytest.raises(WordListError, match="empty"):
        load_word_file(path)


def test_load_rejects_missing_file(tmp_path):
    with pytest.raises(WordListError, match="not found"):
        load_word_file(tmp_path / "missing.txt")


def test_manager_requires_all_three_lists(tmp_path):
    (tmp_path / "easy.txt").write_text("cat\n", encoding="utf-8")
    (tmp_path / "medium.txt").write_text("garden\n", encoding="utf-8")
    with pytest.raises(WordListError):
        WordManager(tmp_path)


# ----- difficulty handling and selection ---------------------------------

def test_manager_uses_custom_directory(tmp_path):
    manager = WordManager(write_lists(tmp_path))
    assert manager.random_word("easy") == "cat"
    assert manager.random_word("medium") == "garden"
    assert manager.random_word("hard") == "rhythm"


def test_difficulty_is_case_insensitive(tmp_path):
    manager = WordManager(write_lists(tmp_path))
    assert manager.random_word("EASY") == "cat"
    assert manager.random_word(" Hard ") == "rhythm"


@pytest.mark.parametrize("bad", ["", "expert", "easyy", None, 1, ["easy"]])
def test_invalid_difficulty_is_rejected(tmp_path, bad):
    manager = WordManager(write_lists(tmp_path))
    with pytest.raises(InvalidDifficultyError):
        manager.random_word(bad)


def test_normalize_difficulty():
    assert normalize_difficulty("Medium") == "medium"
    with pytest.raises(InvalidDifficultyError):
        normalize_difficulty("impossible")


def test_seeded_rng_is_reproducible(tmp_path):
    write_lists(tmp_path, easy="ant\nbee\ncat\ndog\nelk\nfox\n")
    first = WordManager(tmp_path, rng=random.Random(42))
    second = WordManager(tmp_path, rng=random.Random(42))
    picks_a = [first.random_word("easy") for _ in range(10)]
    picks_b = [second.random_word("easy") for _ in range(10)]
    assert picks_a == picks_b


def test_random_selection_uses_whole_list(tmp_path):
    write_lists(tmp_path, easy="ant\nbee\ncat\n")
    manager = WordManager(tmp_path, rng=random.Random(0))
    picks = {manager.random_word("easy") for _ in range(200)}
    assert picks == {"ant", "bee", "cat"}
