"""Word loading and random word selection for Hangman.

Word lists live in ``words/<difficulty>.txt``, one word per line.
Blank lines and lines starting with ``#`` are ignored. Words are
normalized to lowercase, must contain only the letters a-z, and
accidental duplicates are removed (the first occurrence is kept).

This module has no dependency on Flask or any user interface.
"""

from __future__ import annotations

import random
from pathlib import Path

DIFFICULTIES = ("easy", "medium", "hard")

DEFAULT_WORDS_DIR = Path(__file__).resolve().parent / "words"


class InvalidDifficultyError(ValueError):
    """Raised when a difficulty other than easy, medium, or hard is requested."""


class WordListError(ValueError):
    """Raised when a word list file is missing, empty, or contains invalid words."""


def is_valid_word(word: str) -> bool:
    """Return True if ``word`` is non-empty and made only of ASCII letters."""
    return bool(word) and word.isascii() and word.isalpha()


def normalize_difficulty(difficulty: object) -> str:
    """Return the difficulty in lowercase, or raise InvalidDifficultyError."""
    if not isinstance(difficulty, str):
        raise InvalidDifficultyError(
            f"Difficulty must be one of {', '.join(DIFFICULTIES)}."
        )
    value = difficulty.strip().lower()
    if value not in DIFFICULTIES:
        raise InvalidDifficultyError(
            f"Invalid difficulty {difficulty!r}. "
            f"Choose one of: {', '.join(DIFFICULTIES)}."
        )
    return value


def load_word_file(path: str | Path) -> list[str]:
    """Load, validate, and de-duplicate the words in one word list file."""
    path = Path(path)
    if not path.is_file():
        raise WordListError(f"Word list not found: {path}")

    try:
        text = path.read_text(encoding="utf-8-sig")  # tolerate a Notepad BOM
    except UnicodeDecodeError as error:
        raise WordListError(
            f"{path.name} is not valid UTF-8 text; re-save it as UTF-8."
        ) from error

    words: list[str] = []
    seen: set[str] = set()
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        word = line.lower()
        if not is_valid_word(word):
            raise WordListError(
                f"{path.name} line {line_number}: {line!r} must contain "
                "only the letters a-z."
            )
        if word not in seen:
            seen.add(word)
            words.append(word)

    if not words:
        raise WordListError(f"Word list is empty: {path}")
    return words


class WordManager:
    """Loads the Easy, Medium, and Hard word lists and picks random words."""

    def __init__(
        self,
        words_dir: str | Path = DEFAULT_WORDS_DIR,
        rng: random.Random | None = None,
    ) -> None:
        self.words_dir = Path(words_dir)
        self._rng = rng or random.Random()
        self._words: dict[str, tuple[str, ...]] = {
            difficulty: tuple(load_word_file(self.words_dir / f"{difficulty}.txt"))
            for difficulty in DIFFICULTIES
        }

    def get_words(self, difficulty: str) -> tuple[str, ...]:
        """Return every word for a difficulty level."""
        return self._words[normalize_difficulty(difficulty)]

    def random_word(self, difficulty: str) -> str:
        """Return a random word from the requested difficulty level."""
        return self._rng.choice(self.get_words(difficulty))
