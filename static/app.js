// Hangman browser client.
//
// This file contains NO game logic and never knows the hidden word during
// play. It sends requests to the Flask REST API and draws whatever state the
// server returns. The server decides whether a guess is right, wrong, a
// duplicate, a win, or a loss.

"use strict";

(() => {
  const LETTERS = "abcdefghijklmnopqrstuvwxyz".split("");

  const els = {
    controls: document.getElementById("controls"),
    pattern: document.getElementById("pattern"),
    remaining: document.getElementById("remaining"),
    guessed: document.getElementById("guessed"),
    misses: document.getElementById("misses"),
    message: document.getElementById("message"),
    keyboard: document.getElementById("keyboard"),
    drawingLabel: document.getElementById("drawing-label"),
    parts: Array.from(document.querySelectorAll("#drawing .part")),
  };

  let game = null;   // the last state the server sent us
  let busy = false;  // true while a request is in flight, so clicks can't race

  // ----- talking to the server ---------------------------------------------

  class ApiError extends Error {
    constructor(message, status) {
      super(message);
      this.status = status;
    }
  }

  async function api(path, options = {}) {
    let response;
    try {
      response = await fetch(path, {
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        ...options,
      });
    } catch {
      throw new ApiError("Can't reach the server. Check your connection and try again.", 0);
    }

    let data = null;
    try {
      data = await response.json();
    } catch {
      // Non-JSON body; handled below.
    }

    if (!response.ok) {
      const message = (data && data.error) || `The server returned an error (${response.status}).`;
      throw new ApiError(message, response.status);
    }
    return data;
  }

  function selectedDifficulty() {
    const checked = els.controls.querySelector('input[name="difficulty"]:checked');
    return checked ? checked.value : "medium";
  }

  async function newGame() {
    if (busy) return;
    busy = true;
    showMessage("Starting a new game…");
    try {
      game = await api("/api/games", {
        method: "POST",
        body: JSON.stringify({ difficulty: selectedDifficulty() }),
      });
      render();
    } catch (error) {
      showMessage(error.message, "error");
    } finally {
      busy = false;
    }
  }

  async function guess(letter) {
    if (busy || !game || game.status !== "playing") return;
    if (game.guessed_letters.includes(letter)) return;  // key is already disabled

    busy = true;
    try {
      game = await api(`/api/games/${encodeURIComponent(game.game_id)}/guess`, {
        method: "POST",
        body: JSON.stringify({ letter }),
      });
      render();
    } catch (error) {
      await handleGuessError(error);
    } finally {
      busy = false;
    }
  }

  async function handleGuessError(error) {
    if (error.status === 404) {
      // The server forgot this game, e.g. it restarted or the host put it to sleep.
      game = null;
      render();
      showMessage("This game is no longer on the server. Start a new game to keep playing.", "error");
      return;
    }
    if (error.status === 409 && game) {
      // Already guessed or already over: re-sync with the server's view.
      try {
        game = await api(`/api/games/${encodeURIComponent(game.game_id)}`);
        render();
      } catch {
        // Keep the old state; the message below explains what happened.
      }
    }
    showMessage(error.message, "error");
  }

  // ----- drawing the state --------------------------------------------------

  function render() {
    renderPattern();
    renderCounts();
    renderDrawing();
    renderKeyboard();
    renderMessage();
  }

  function renderPattern() {
    els.pattern.replaceChildren();
    if (!game) {
      els.pattern.innerHTML = "&nbsp;";
      return;
    }
    const shown = game.pattern.split(" ");
    els.pattern.style.setProperty("--letters", shown.length);  // sizes the slots to fit
    shown.forEach((char, index) => {
      const slot = document.createElement("span");
      slot.className = "slot";
      if (char === "_") {
        // `word` exists only after the server says the game is over.
        if (game.word) {
          slot.textContent = game.word[index];
          slot.classList.add("missed");
        } else {
          slot.textContent = "\u00a0";
        }
      } else {
        slot.textContent = char;
      }
      els.pattern.append(slot);
    });
    els.pattern.setAttribute(
      "aria-label",
      `Word: ${shown.map((c) => (c === "_" ? "blank" : c)).join(", ")}`
    );
  }

  function renderCounts() {
    if (!game) {
      els.remaining.textContent = "\u00a0";
      els.guessed.textContent = "none yet";
      els.misses.textContent = "none yet";
      return;
    }
    const left = game.remaining_guesses;
    els.remaining.textContent = `${left} wrong ${left === 1 ? "guess" : "guesses"} left`;
    els.remaining.classList.toggle("low", left <= 2);
    els.guessed.textContent = listLetters(game.guessed_letters);
    els.misses.textContent = listLetters(game.incorrect_letters);
  }

  function listLetters(letters) {
    return letters.length ? letters.map((l) => l.toUpperCase()).join(" ") : "none yet";
  }

  function renderDrawing() {
    const wrong = game ? game.incorrect_letters.length : 0;
    els.parts.forEach((part) => {
      part.classList.toggle("drawn", Number(part.dataset.part) <= wrong);
    });
    els.drawingLabel.textContent = `Hangman drawing: ${wrong} of ${els.parts.length} parts drawn`;
  }

  function renderKeyboard() {
    const guessed = game ? game.guessed_letters : [];
    const misses = game ? game.incorrect_letters : [];
    const playing = Boolean(game) && game.status === "playing";

    els.keyboard.querySelectorAll(".key").forEach((key) => {
      const letter = key.dataset.letter;
      const used = guessed.includes(letter);
      key.disabled = used || !playing;
      key.classList.toggle("hit", used && !misses.includes(letter));
      key.classList.toggle("miss", misses.includes(letter));
    });
  }

  function renderMessage() {
    if (!game) return;
    const word = game.word ? game.word.toUpperCase() : "";
    if (game.status === "won") {
      showMessage(`You got it! The word was ${word}.`, "won");
    } else if (game.status === "lost") {
      showMessage(`Out of guesses. The word was ${word}.`, "lost");
    } else {
      showMessage("");
    }
  }

  function showMessage(text, kind = "") {
    els.message.textContent = text;
    els.message.className = `message ${kind}`.trim();
  }

  // ----- input ---------------------------------------------------------------

  function buildKeyboard() {
    LETTERS.forEach((letter) => {
      const key = document.createElement("button");
      key.type = "button";
      key.className = "key";
      key.dataset.letter = letter;
      key.textContent = letter.toUpperCase();
      key.setAttribute("aria-label", `Guess ${letter.toUpperCase()}`);
      key.addEventListener("click", () => guess(letter));
      els.keyboard.append(key);
    });
  }

  document.addEventListener("keydown", (event) => {
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    const letter = event.key.toLowerCase();
    if (letter.length === 1 && letter >= "a" && letter <= "z") {
      event.preventDefault();
      guess(letter);
    }
  });

  els.controls.addEventListener("submit", (event) => {
    event.preventDefault();  // start a new game without reloading the page
    newGame();
  });

  buildKeyboard();
  render();
  newGame();
})();
