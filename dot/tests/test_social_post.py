"""Check the social-post checker's channel limits and paste hazards."""

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "skills/social-post/scripts/check_post.py"


@pytest.fixture
def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("social_post_check", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_x_weight_counts_urls_emoji_and_cjk(checker: ModuleType) -> None:
    assert checker.x_weight("abc") == 3
    assert checker.x_weight("see https://www.fmind.dev/articles/a-very-long-slug/") == 4 + 23
    assert checker.x_weight("\U0001f469\u200d\U0001f4bb") == 2
    assert checker.x_weight("\u65e5\u672c") == 4
    assert checker.x_weight("e\u0301") == 1


def test_bluesky_counts_flags_and_sequences_once(checker: ModuleType) -> None:
    assert len(checker.clusters("\U0001f1f1\U0001f1fa\U0001f44b\U0001f3fd")) == 2


def test_clean_posts_pass(checker: ModuleType) -> None:
    linkedin = "One claim.\n\n\nOne detail https://www.fmind.dev/articles/x/?utm_source=linkedin #MLOps\n"
    assert checker.check("linkedin", linkedin) == ([], [])
    assert checker.check("x", "First block.\n---\nSecond block.\n") == ([], [])
    assert checker.check("bluesky", "I rebuilt my todo app; the date is tbd.\n") == ([], [])


@pytest.mark.parametrize(
    ("channel", "text", "fragment"),
    [
        ("linkedin", "Use **bold** here", "Markdown bold"),
        ("linkedin", "## Heading\nText", "Markdown heading"),
        ("x", "Read [this](https://example.com)", "Markdown link"),
        ("x", "Fast \u2014 and cheap", "em-dash"),
        ("x", "Read it at <article url>", "placeholder"),
        ("x", "Read it at <Article URL>", "placeholder"),
        ("x", "TODO add the link", "placeholder"),
        ("x", "#a #b #c", "hashtags"),
        ("x", "a" * 281, "281/280"),
        ("x", "ok\n---\n\n---\nok", "block 2: empty"),
        ("bluesky", "\u00e9" * 301, "301/300"),
        ("linkedin", "Text. Link in the first comment.", "link-in-comment"),
        ("linkedin", "   ", "empty copy"),
    ],
)
def test_hazards_fail(checker: ModuleType, channel: str, text: str, fragment: str) -> None:
    errors, _ = checker.check(channel, text)
    assert any(fragment in error for error in errors), errors


def test_linkedin_warnings(checker: ModuleType) -> None:
    _, warnings = checker.check("linkedin", "x" * 201 + "\n\nSee https://www.fmind.dev/articles/a/ and `uv run`")
    assert any("first line" in warning for warning in warnings)
    assert any("one empty line" in warning for warning in warnings)
    assert any("utm_source" in warning for warning in warnings)
    assert any("backticks" in warning for warning in warnings)


def test_cli_exit_status(tmp_path: Path) -> None:
    good = tmp_path / "x.txt"
    good.write_text("Plain post.\n", encoding="utf-8")
    passed = subprocess.run([sys.executable, str(SCRIPT), "--channel", "x", str(good)], capture_output=True, text=True)
    assert passed.returncode == 0
    assert passed.stdout.startswith("OK x")
    failed = subprocess.run(
        [sys.executable, str(SCRIPT), "--channel", "x", "-"], input="a **b**", capture_output=True, text=True
    )
    assert failed.returncode == 1
    assert "ERROR x" in failed.stdout
    unreadable = subprocess.run(
        [sys.executable, str(SCRIPT), "--channel", "x", str(tmp_path / "missing.txt")], capture_output=True, text=True
    )
    assert unreadable.returncode == 2
    assert "Cannot read" in unreadable.stderr
