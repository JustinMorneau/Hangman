"""Core Hangman game engine.

``HangmanGame`` holds one game's hidden word and rules. It has no
dependency on Flask, the browser, or any other user interface, so it
can be tested entirely on its own.

The hidden word is only exposed through ``to_dict()`` after the game
has ended.
"""

from __future__ import annotations

from word_manager import is_valid_word, normalize_difficulty

MAX_INCORRECT_GUESSES = 6

STATUS_PLAYING = "playing"
STATUS_WON = "won"
STATUS_LOST = "lost"


class GuessError(ValueError):
    """Base class for rejected guesses. A rejected guess never changes state."""


class InvalidGuessError(GuessError):
    """The guess is not exactly one letter a-z."""


class DuplicateGuessError(GuessError):
    """The letter has already been guessed in this game."""


class GameOverError(GuessError):
    """The game has already been won or lost."""


def normalize_letter(letter: object) -> str:
    """Return ``letter`` as a single lowercase letter, or raise InvalidGuessError."""
    if not isinstance(letter, str):
        raise InvalidGuessError("Guess must be a single letter.")
    value = letter.strip().lower()
    if len(value) != 1 or not is_valid_word(value):
        raise InvalidGuessError("Guess must be a single letter a-z.")
    return value


class HangmanGame:
    """One game of Hangman."""

    def __init__(
        self,
        word: str,
        difficulty: str = "medium",
        max_incorrect: int = MAX_INCORRECT_GUESSES,
    ) -> None:
        if not isinstance(word, str) or not is_valid_word(word.strip()):
            raise ValueError("The hidden word must contain only the letters a-z.")
        if max_incorrect < 1:
            raise ValueError("max_incorrect must be at least 1.")

        self._word = word.strip().lower()
        self.difficulty = normalize_difficulty(difficulty)
        self.max_incorrect = max_incorrect
        self._guessed: list[str] = []  # every accepted guess, in order

    # ----- derived state -------------------------------------------------

    @property
    def guessed_letters(self) -> list[str]:
        return list(self._guessed)

    @property
    def correct_letters(self) -> list[str]:
        return [letter for letter in self._guessed if letter in self._word]

    @property
    def incorrect_letters(self) -> list[str]:
        return [letter for letter in self._guessed if letter not in self._word]

    @property
    def remaining_guesses(self) -> int:
        return self.max_incorrect - len(self.incorrect_letters)

    @property
    def pattern(self) -> str:
        """The masked word, e.g. ``"_ e _ _ e"``."""
        return " ".join(
            letter if letter in self._guessed else "_" for letter in self._word
        )

    @property
    def status(self) -> str:
        if all(letter in self._guessed for letter in self._word):
            return STATUS_WON
        if self.remaining_guesses <= 0:
            return STATUS_LOST
        return STATUS_PLAYING

    @property
    def is_over(self) -> bool:
        return self.status != STATUS_PLAYING

    # ----- actions -------------------------------------------------------

    def guess(self, letter: object) -> bool:
        """Apply one guess and return True if the letter is in the word.

        Raises GameOverError, InvalidGuessError, or DuplicateGuessError
        without changing the game state.
        """
        if self.is_over:
            raise GameOverError(f"The game is already {self.status}.")
        value = normalize_letter(letter)
        if value in self._guessed:
            raise DuplicateGuessError(f"The letter {value!r} was already guessed.")
        self._guessed.append(value)
        return value in self._word

    # ----- serialization -------------------------------------------------

    def to_dict(self) -> dict:
        """Return a client-safe snapshot of the game.

        ``word`` is included only after the game is won or lost.
        """
        state = {
            "difficulty": self.difficulty,
            "pattern": self.pattern,
            "word_length": len(self._word),
            "guessed_letters": self.guessed_letters,
            "correct_letters": self.correct_letters,
            "incorrect_letters": self.incorrect_letters,
            "remaining_guesses": self.remaining_guesses,
            "max_incorrect": self.max_incorrect,
            "status": self.status,
        }
        if self.is_over:
            state["word"] = self._word
        return state
