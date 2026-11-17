"""Persona, supagents, and skills never reintroduce shortcut-licensing slogans."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

SHORTCUT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("80/20 slogan", re.compile(r"\b80[/ -]20\b", re.IGNORECASE)),
    ("signal-over-completeness slogan", re.compile(r"\bsignal over completeness\b", re.IGNORECASE)),
    ("fixed 1-to-3 signal cap", re.compile(r"\bkeep 1 to 3\b", re.IGNORECASE)),
    ("single-guide blindfold", re.compile(r"\bread only the (?:matching|selected) guide\b", re.IGNORECASE)),
    ("skip-builds-or-tests shortcut", re.compile(r"\bskip builds/tests\b", re.IGNORECASE)),
    ("skip-version-probe blindfold", re.compile(r"\bskip ritual --version\b", re.IGNORECASE)),
    ("smallest-useful-repo shortcut", re.compile(r"\bsmallest useful repository\b", re.IGNORECASE)),
)


def find_shortcut_phrases(text: str) -> list[tuple[int, str, str]]:
    hits: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for label, pattern in SHORTCUT_PATTERNS:
            if pattern.search(line):
                hits.append((lineno, label, line.strip()))
    return hits


def _instruction_markdown_files() -> list[Path]:
    files = [ROOT / "AGENTS.md", ROOT / "dot_agents/AGENTS.md"]
    files.extend(sorted((ROOT / "dot_agents/supagents").glob("*.md")))
    files.extend(sorted((ROOT / "skills").rglob("*.md")))
    files.extend(sorted((ROOT / ".agents/skills").rglob("*.md")))
    return files


def test_instruction_markdown_excludes_shortcut_licensing_phrases() -> None:
    files = _instruction_markdown_files()
    assert len(files) >= 100
    violations = [
        f"{path.relative_to(ROOT)}:{lineno} ({label}): {snippet}"
        for path in files
        for lineno, label, snippet in find_shortcut_phrases(path.read_text(encoding="utf-8"))
    ]
    assert violations == []


@pytest.mark.parametrize(
    ("sample", "expected_label"),
    [
        ("Adhere to the 80/20, YAGNI, and KISS principles.", "80/20 slogan"),
        ("Apply an 80-20 rule when reviewing.", "80/20 slogan"),
        ("Prefer signal over completeness in summaries.", "signal-over-completeness slogan"),
        ("Keep 1 to 3 signals per message.", "fixed 1-to-3 signal cap"),
        ("Read only the matching guide and its resources.", "single-guide blindfold"),
        ("Read only the selected guide and its linked resources.", "single-guide blindfold"),
        ("Skip builds/tests unless needed.", "skip-builds-or-tests shortcut"),
        ("Reuse context and skip ritual --version probes.", "skip-version-probe blindfold"),
        ("Generate the smallest useful repository.", "smallest-useful-repo shortcut"),
    ],
)
def test_shortcut_phrase_detector_flags_banned_slogans(sample: str, expected_label: str) -> None:
    hits = find_shortcut_phrases(sample)
    assert [label for _, label, _ in hits] == [expected_label]
