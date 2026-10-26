# Testing

This project is tested in two ways: an automated test suite (pytest), and a
manual checklist for the browser client.

## Running the automated tests

From the repository root, with the virtual environment active:

```bash
python -m pip install -r requirements.txt
python -m pip install playwright            # only needed for the browser tests
python -m playwright install chromium
python -m pytest -v
```

Expected result: **156 passed**. Without Playwright installed, the 18 browser
tests are reported as skipped and everything else still runs.

| File | Tests | What it covers |
|---|---|---|
| `tests/test_word_manager.py` | 28 | Loading the word lists: comments, case, duplicates, non-letters, empty, missing, and non-UTF-8 files; random selection by difficulty; invalid difficulty |
| `tests/test_game.py` | 42 | Game engine with no server: correct, incorrect, invalid, and duplicate guesses; win and loss; no guesses after the game ends; the word is hidden until the end |
| `tests/test_server.py` | 55 | REST API: all three endpoints, status codes (201, 200, 400, 404, 405, 409, 413), malformed requests, separate game states, the word never appearing in any response while playing |
| `tests/test_client.py` | 7 | The page and its files are served; the JavaScript calls the API and contains no word lists or guess-checking logic |
| `tests/test_end_to_end.py` | 6 | 120 complete games against the real word lists with the rules checked after every guess; a full game over real HTTP; simultaneous requests to one game |
| `tests/test_browser.py` | 18 | Real Chromium against a live server: every difficulty, clicking and typing letters, drawing updates, win, loss, new game without reload, word hidden on the page, layout at 320, 375, 768, and 1280 px wide |

`tests/conftest.py` holds the shared live-server fixture. Its known words
are easy = `apple`, medium = `garden`, and hard = `extravaganza`.

## Manual browser checklist

Run `python server.py`, open <http://127.0.0.1:5000>, and fill in the Result
column (Pass / Fail plus a note). Repeat on the deployed URL after Phase 5.

| # | Check | Expected | Result |
|---|---|---|---|
| 1 | Load the page | A Medium game starts on its own; blank slots, "6 wrong guesses left", no drawing parts |X|
| 2 | Select Easy, click New game | A new, shorter word; previous guesses cleared |X|
| 3 | Select Hard, click New game | A new hard word; previous guesses cleared |X|
| 4 | Click a letter that is in the word | Letter appears in every matching slot; key turns blue and disables; count unchanged |X|
| 5 | Type a letter that is not in the word | One body part draws in; key turns red and is crossed out; count drops by one; letter listed under Misses |X|
| 6 | Type the same letter again | Nothing happens; no error |X|
| 7 | Type a number or symbol | Nothing happens |X|
| 8 | Win a game | "You got it! The word was …"; all keys disabled |X|
| 9 | Lose a game | All six parts drawn; "Out of guesses. The word was …"; missing letters shown in red; keys disabled |X|
| 10 | Click New game after a win or loss | Fresh game without the page reloading |X|
| 11 | Play using only the keyboard (Tab to the controls, type letters) | Everything works; focus outline visible |X|
| 12 | Switch the OS or browser to dark mode | Chalkboard theme; all text readable |X|
| 13 | DevTools device toolbar: iPhone SE (375 px) and a 320 px width | No sideways scrolling; word on one line; keys tappable |X|
| 14 | Stop the server mid-game, then guess | Message says the server can't be reached |X|
| 15 | Restart the server, then guess in the old game | Message says the game is no longer on the server; New game works |X|

### Checking the network tab for answer leaks

1. Open DevTools (F12) → **Network** → filter by **Fetch/XHR**.
2. Start a game and make a few guesses without finishing.
3. Click each `games` and `guess` request → **Response**. There must be no
   `word` field while `status` is `"playing"`.
4. Finish the game. Only the final response should contain `word`.
5. Also check **Sources** → `app.js`: it contains no word lists.

Result: ______

## Bugs found and fixed

| # | Phase | Bug | Fix | Regression test |
|---|---|---|---|---|
| 1 | 1 | On Windows, test files were written in cp1252, and the loader crashed with a raw `UnicodeDecodeError` on non-UTF-8 word files | Tests write UTF-8 explicitly; the loader reports a clear `WordListError` and accepts a Notepad byte-order mark | `test_load_rejects_file_that_is_not_utf8`, `test_load_accepts_utf8_with_byte_order_mark` |
| 2 | 3 | A test helper counted the "none yet" placeholder as two guesses | Count marked keys instead | Covered by every browser test |
| 3 | 4 | The server accepted request bodies of any size (5 MB was accepted) | 16 KB limit; larger requests get a JSON HTTP 413 | `test_oversized_create_request_returns_413`, `test_oversized_guess_request_returns_413_and_changes_nothing` |
| 4 | 4 | On 320 px phones, long words wrapped onto two lines and the keyboard made the page scroll sideways | Word never wraps and its letters scale to fit; phone keys keep a 44 px height but may narrow | `test_layout_fits_screen[320-640]`, `test_layout_fits_screen[375-812]` |
| 5 | 4 | At tablet width (768 px), a 12-letter word overflowed its column by 193 px because letters were sized to the screen, not the column | Letters sized with container units (`cqi`) relative to their own column | `test_layout_fits_screen[768-1024]` |
| 6 | 4 | Letters floated above their underlines when the word was scaled down | Slots align to the bottom of the row | Checked visually |
