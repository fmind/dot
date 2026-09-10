"""Exercise the installed-shape helpers with local content and no gws executable."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "skills/gws/scripts"


def run_helper(
    tmp_path: Path, name: str, content: str, *args: str, stdin: bool = False
) -> subprocess.CompletedProcess[str]:
    source = tmp_path / "content.txt"
    source.write_text(content, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPTS / f"{name}.py"), "-" if stdin else str(source), *args],
        input=content if stdin else None,
        text=True,
        capture_output=True,
        cwd=tmp_path,
        env={**os.environ, "PATH": str(tmp_path)},
        check=False,
    )


def test_chat_preserves_unicode_newlines_shell_text_and_code(tmp_path: Path) -> None:
    text = "*Update*\n- Médéric 😀\n`$(touch SHOULD_NOT_EXIST)` and `**kwargs`\n```\n# literal **code**\n```\n"
    result = run_helper(tmp_path, "chat_body", text, "--thread", "spaces/example/threads/topic", stdin=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"text": text, "thread": {"name": "spaces/example/threads/topic"}}
    assert not (tmp_path / "SHOULD_NOT_EXIST").exists()
    assert result.stderr == ""


def test_chat_markdown_is_explicit_and_preserves_body(tmp_path: Path) -> None:
    text = "**Ready**\n[Read](https://example.com)\n"
    result = run_helper(tmp_path, "chat_body", text, "--syntax", "markdown")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"text": text, "markupSyntax": "MARKUP_SYNTAX_MARKDOWN"}


@pytest.mark.parametrize(
    ("text", "args", "diagnostic"),
    [
        (" \n", (), "empty"),
        ("# Heading\n", (), "bold label"),
        ("| A | B |\n| --- | --- |\n", (), "table"),
        ("**bold**", (), "--syntax markdown"),
        ("[link](https://example.com)", (), "--syntax markdown"),
        ("```python\npass\n```", (), "language label"),
        ("```\nmissing end", (), "Close"),
        ("😀" * 7501, (), "30000-byte"),
        ("Ready", ("--thread", "spaces/example/messages/wrong"), "Thread"),
    ],
)
def test_chat_rejects_broken_requests(tmp_path: Path, text: str, args: tuple[str, ...], diagnostic: str) -> None:
    result = run_helper(tmp_path, "chat_body", text, *args)
    assert result.returncode == 1
    assert result.stdout == ""
    assert diagnostic in result.stderr


def test_pages_preserve_unicode_and_combine_pretty_json(tmp_path: Path) -> None:
    pages = [{"files": [{"name": "a\u2028b"}], "nextPageToken": "next"}, {"files": [{"name": "second"}]}]
    result = run_helper(
        tmp_path, "pages", "\n".join(json.dumps(p, ensure_ascii=False, indent=2) for p in pages), "--items", "files"
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["items"] == [{"name": "a\u2028b"}, {"name": "second"}]
    assert data["complete"] is True
    assert data["pageCount"] == 2


@pytest.mark.parametrize(
    "text", ["", "not json", "[]", '{"error":{"message":"PRIVATE"}}', '{"files":{}}', '{"nextPageToken":5}', "{}\n{}"]
)
def test_pages_reject_invalid_streams_without_exposing_content(tmp_path: Path, text: str) -> None:
    result = run_helper(tmp_path, "pages", text, "--items", "files")
    assert result.returncode == 1
    assert result.stdout == ""
    assert "PRIVATE" not in result.stderr


@pytest.mark.parametrize("partial", [{"nextPageToken": "next"}, {"incompleteSearch": True}])
def test_pages_partial_data_requires_explicit_choice(tmp_path: Path, partial: dict[str, object]) -> None:
    text = json.dumps({"files": [{"id": "one"}], **partial})
    result = run_helper(tmp_path, "pages", text, "--items", "files")
    assert result.returncode == 1
    assert "incomplete" in result.stderr
    result = run_helper(tmp_path, "pages", text, "--items", "files", "--allow-incomplete")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["complete"] is False


def paragraph(text: str) -> dict[str, object]:
    return {"paragraph": {"elements": [{"textRun": {"content": text}}]}}


def test_docs_extract_nested_tabs_table_and_notes_once(tmp_path: Path) -> None:
    child = {
        "tabProperties": {"tabId": "child", "title": "Child"},
        "documentTab": {"body": {"content": [paragraph("child\n")]}},
    }
    table = {
        "table": {"tableRows": [{"tableCells": [{"content": [paragraph("one\n")]}, {"content": [paragraph("two\n")]}]}]}
    }
    document = {
        "documentId": "doc",
        "body": {"content": [paragraph("legacy duplicate")]},
        "tabs": [
            {
                "tabProperties": {"tabId": "parent", "title": "Parent"},
                "documentTab": {
                    "body": {"content": [paragraph("intro 😀\n"), table]},
                    "headers": {"h": {"content": [paragraph("heading\n")]}},
                    "footers": {"f": {"content": [paragraph("footer\n")]}},
                    "footnotes": {"n": {"content": [paragraph("note\n")]}},
                },
                "childTabs": [child],
            }
        ],
    }
    result = run_helper(tmp_path, "docs_text", json.dumps(document))
    assert result.returncode == 0, result.stderr
    sections = json.loads(result.stdout)["sections"]
    assert [section["text"] for section in sections] == [
        "intro 😀\none\ttwo\n",
        "heading\n",
        "footer\n",
        "note\n",
        "child\n",
    ]
    assert sections[-1]["tabId"] == "child"
    assert "legacy duplicate" not in result.stdout


def test_docs_legacy_labels_first_tab_coverage(tmp_path: Path) -> None:
    result = run_helper(tmp_path, "docs_text", json.dumps({"body": {"content": [paragraph("first")]}}))
    assert result.returncode == 0, result.stderr
    assert "first tab" in json.loads(result.stdout)["coverage"]


@pytest.mark.parametrize(
    "text",
    ["{}", "[]", "null", '{"title":"Metadata only"}', '{"tabs":[{}]}', '{"error":{"message":"PRIVATE"}}', "PRIVATE"],
)
def test_docs_malformed_or_metadata_only_is_not_empty_success(tmp_path: Path, text: str) -> None:
    result = run_helper(tmp_path, "docs_text", text)
    assert result.returncode == 1
    assert result.stdout == ""
    assert "PRIVATE" not in result.stderr
