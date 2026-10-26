"""Phase 3: end-to-end tests that drive a real browser against a live server.

Requires Playwright (optional, not needed by the app itself):

    python -m pip install playwright
    python -m playwright install chromium

If Playwright or its browser is not installed, these tests are skipped.
The live server (see conftest.py) uses one known word per difficulty:
easy = apple, medium = garden, hard = extravaganza.
"""

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from conftest import KNOWN_WORDS  # noqa: E402


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except Exception as error:  # browser binaries not installed
            pytest.skip(f"Chromium not available: {error}")
        yield browser
        browser.close()


@pytest.fixture
def page(browser, live_server):
    page = browser.new_page()
    page.goto(live_server["url"])
    page.wait_for_selector("#pattern .slot")  # first game started automatically
    yield page
    page.close()


# ----- helpers ---------------------------------------------------------------

def slots(page):
    return page.locator("#pattern .slot").all_inner_texts()


def start(page, difficulty):
    page.check(f'input[name="difficulty"][value="{difficulty}"]')
    page.click("#new-game")
    page.wait_for_function(
        "n => document.querySelectorAll('#pattern .slot').length === n",
        arg=len(KNOWN_WORDS[difficulty]),
    )
    page.wait_for_function("!document.querySelector('.key').disabled")


def guess_count(page):
    return page.locator(".key.hit, .key.miss").count()


def click_key(page, letter):
    count = guess_count(page)
    page.click(f'.key[data-letter="{letter}"]')
    wait_for_guess_count(page, count + 1)


def type_key(page, letter):
    count = guess_count(page)
    page.keyboard.press(letter)
    wait_for_guess_count(page, count + 1)


def wait_for_guess_count(page, n):
    """Wait until the server's reply has been drawn: n keys marked hit or miss."""
    page.wait_for_function(
        "n => document.querySelectorAll('.key.hit, .key.miss').length === n",
        arg=n,
    )


def drawn_parts(page):
    return page.locator("#drawing .part.drawn").count()


# ----- tests -----------------------------------------------------------------

def test_page_starts_a_medium_game(page):
    assert slots(page) == ["\u00a0"] * 6
    assert page.inner_text("#remaining") == "6 wrong guesses left"
    assert drawn_parts(page) == 0


@pytest.mark.parametrize("difficulty, length", [("easy", 5), ("medium", 6), ("hard", 12)])
def test_each_difficulty_starts_a_game(page, difficulty, length):
    start(page, difficulty)
    assert len(slots(page)) == length


def test_correct_guess_by_click_updates_page(page):
    start(page, "easy")
    click_key(page, "p")
    assert slots(page)[1:3] == ["p", "p"]
    key = page.locator('.key[data-letter="p"]')
    assert key.is_disabled()
    assert "hit" in key.get_attribute("class")
    assert page.inner_text("#remaining") == "6 wrong guesses left"
    assert drawn_parts(page) == 0


def test_wrong_guess_by_keyboard_updates_page(page):
    start(page, "easy")
    type_key(page, "z")
    assert page.inner_text("#misses") == "Z"
    assert page.inner_text("#remaining") == "5 wrong guesses left"
    assert drawn_parts(page) == 1
    assert "miss" in page.locator('.key[data-letter="z"]').get_attribute("class")


def test_each_wrong_guess_draws_one_more_part(page):
    start(page, "easy")
    for number, letter in enumerate("qrstu", start=1):
        type_key(page, letter)
        assert drawn_parts(page) == number


def test_repeated_key_press_is_ignored(page):
    start(page, "easy")
    type_key(page, "z")
    page.keyboard.press("z")  # duplicate: the client ignores it
    page.wait_for_timeout(300)
    assert page.inner_text("#guessed") == "Z"
    assert page.inner_text("#remaining") == "5 wrong guesses left"
    assert page.inner_text("#message") == ""


def test_non_letter_keys_are_ignored(page):
    start(page, "easy")
    for key in ["1", "!", "Enter", "Space"]:
        page.keyboard.press(key)
    page.wait_for_timeout(300)
    assert page.inner_text("#guessed") == "none yet"


def test_win_shows_message_and_locks_keyboard(page):
    start(page, "easy")
    for letter in "aple":
        click_key(page, letter)
    assert slots(page) == list("apple")
    assert "You got it" in page.inner_text("#message")
    assert "APPLE" in page.inner_text("#message")
    assert page.locator(".key:not([disabled])").count() == 0


def test_loss_shows_message_word_and_full_drawing(page):
    start(page, "easy")
    for letter in "qrstuv":
        type_key(page, letter)
    assert drawn_parts(page) == 6
    assert page.inner_text("#remaining") == "0 wrong guesses left"
    assert "Out of guesses" in page.inner_text("#message")
    assert slots(page) == list("apple")  # revealed after the loss
    assert page.locator(".key:not([disabled])").count() == 0


def test_new_game_after_finishing_without_reload(page):
    page.evaluate("window.__noReload = true")  # disappears if the page reloads
    start(page, "easy")
    for letter in "aple":
        click_key(page, letter)
    start(page, "hard")
    assert page.evaluate("window.__noReload") is True
    assert slots(page) == ["\u00a0"] * 12
    assert page.inner_text("#message") == ""
    assert page.inner_text("#guessed") == "none yet"
    assert drawn_parts(page) == 0
    assert page.locator(".key[disabled]").count() == 0


def test_word_not_in_page_while_playing(page):
    start(page, "easy")
    click_key(page, "p")
    click_key(page, "z")
    assert "apple" not in page.content().lower()
    assert "apple" not in page.locator("body").inner_text().lower()


def test_lost_game_on_server_shows_helpful_message(page, live_server):
    start(page, "easy")
    live_server["app"].config["GAME_STORE"]._games.clear()  # simulate a server restart
    page.keyboard.press("e")
    page.wait_for_function(
        "document.getElementById('message').textContent.includes('no longer')"
    )
    assert page.locator(".key:not([disabled])").count() == 0


# ----- layout at phone, tablet, and desktop sizes (Phase 4) ------------------

@pytest.mark.parametrize("width, height", [(320, 640), (375, 812), (768, 1024), (1280, 800)])
def test_layout_fits_screen(browser, live_server, width, height):
    """Regression test: long words used to wrap onto two lines and the
    keyboard overflowed sideways on 320px phones."""
    page = browser.new_page(viewport={"width": width, "height": height})
    try:
        page.goto(live_server["url"])
        page.wait_for_selector("#pattern .slot")
        start(page, "hard")  # 12-letter word, the worst case
        for letter in "xtr":
            type_key(page, letter)

        overflow = page.evaluate(
            "document.documentElement.scrollWidth - document.documentElement.clientWidth"
        )
        assert overflow <= 0, f"page scrolls sideways by {overflow}px"

        rows = page.evaluate(
            "new Set([...document.querySelectorAll('#pattern .slot')]"
            ".map(s => Math.round(s.getBoundingClientRect().top))).size"
        )
        assert rows == 1, "the word wrapped onto more than one line"

        key = page.locator(".key").first.bounding_box()
        assert key["height"] >= 40, "keys are too small to tap"
        assert page.locator("#drawing").is_visible()
        assert page.locator("#new-game").is_visible()
    finally:
        page.close()
