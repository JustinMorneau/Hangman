"""Phase 5: checks that the project is configured correctly for Render.

These guard against the most common deployment mistakes. The final check,
playing games on the public URL, is done with smoke_test.py after deploying.
"""

import re
from pathlib import Path

import smoke_test
from server import app

ROOT = Path(__file__).resolve().parent.parent


def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


def test_production_app_is_not_in_debug_mode():
    """Gunicorn imports `server:app`; debug mode must be off for it."""
    assert app.debug is False


def test_runtime_requirements():
    requirements = read("requirements.txt").lower()
    assert re.search(r"^flask", requirements, re.M)
    assert re.search(r"^gunicorn", requirements, re.M)
    # test tools stay out of the production install
    assert "pytest" not in requirements and "playwright" not in requirements


def test_dev_requirements_include_runtime_and_tests():
    dev = read("requirements-dev.txt")
    assert "-r requirements.txt" in dev
    assert "pytest" in dev


def test_python_version_is_pinned():
    version = read(".python-version").strip()
    assert re.fullmatch(r"3\.\d+(\.\d+)?", version)


def test_render_blueprint():
    blueprint = read("render.yaml")
    assert "type: web" in blueprint
    assert "runtime: python" in blueprint
    assert "plan: free" in blueprint  # otherwise Render picks a paid plan
    assert "pip install -r requirements.txt" in blueprint
    start = re.search(r"startCommand:\s*(.+)", blueprint).group(1)
    assert "gunicorn" in start
    assert "$PORT" in start                # Render chooses the port
    assert "0.0.0.0" in start              # listen on all interfaces, not localhost
    assert "--workers 1" in start          # games live in one process's memory
    assert start.strip().endswith("server:app")


def test_browser_uses_relative_api_urls():
    """Absolute localhost URLs would work locally but break once deployed."""
    js = read("static/app.js")
    assert "localhost" not in js and "127.0.0.1" not in js
    assert not re.search(r"fetch\(\s*[\"'`]https?://", js)


def test_smoke_test_passes_against_live_server(live_server, capsys):
    assert smoke_test.SmokeTest(live_server["url"]).run() is True
    output = capsys.readouterr().out
    assert "FAIL" not in output
