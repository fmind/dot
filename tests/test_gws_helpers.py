"""Exercise the installed-shape helpers with local content and no gws executable."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from repo_helpers import ROOT, load_script

SCRIPTS = ROOT / "skills/gws/scripts"


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
        timeout=30,
    )


def test_chat_preserves_unicode_newlines_shell_text_and_code(tmp_path: Path) -> None:
    text = "*Update*\n- Médéric 😀\n`$(touch SHOULD_NOT_EXIST)` and `**kwargs`\n```\n# literal **code**\n```\n"
    result = run_helper(tmp_path, "chat_body", text, "--thread", "spaces/example/threads/topic", stdin=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "text": text,
        "markupSyntax": "MARKUP_SYNTAX_CHAT",
        "thread": {"name": "spaces/example/threads/topic"},
    }
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


def test_docs_smart_chips_become_labeled_placeholders(tmp_path: Path) -> None:
    elements = [
        {"textRun": {"content": "Owner "}},
        {"person": {"personProperties": {"name": "Ada Lovelace", "email": "ada@example.com"}}},
        {"person": {"personProperties": {"email": "grace@example.com"}}},
        {"richLink": {"richLinkProperties": {"title": "Q3 plan", "uri": "https://example.com/q3"}}},
        {"dateElement": {"dateElementProperties": {"displayText": "Oct 2, 2026"}}},
        {"dateElement": {}},
        {"textRun": {"content": "\n"}},
    ]
    document = {"body": {"content": [{"paragraph": {"elements": elements}}]}}
    result = run_helper(tmp_path, "docs_text", json.dumps(document))
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["sections"][0]["text"] == (
        "Owner [person: Ada Lovelace][person: grace@example.com][link: Q3 plan][date: Oct 2, 2026][date]\n"
    )


@pytest.mark.parametrize(
    ("properties", "expected"),
    [
        ({"displayValue": "Blocked"}, "Status: [dropdown: Blocked]\n"),
        ({"displayValue": "En cours"}, "Status: [dropdown: En cours]\n"),  # typos: ignore-line
        ({}, "Status: [dropdown]\n"),
        ({"displayValue": ""}, "Status: [dropdown]\n"),
    ],
)
def test_docs_dropdown_preserves_selected_text(tmp_path: Path, properties: dict[str, str], expected: str) -> None:
    elements = [
        {"textRun": {"content": "Status: "}},
        {"dropdown": {"dropdownProperties": properties}},
        {"textRun": {"content": "\n"}},
    ]
    document = {"body": {"content": [{"paragraph": {"elements": elements}}]}}
    result = run_helper(tmp_path, "docs_text", json.dumps(document))
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["sections"][0]["text"] == expected


@pytest.mark.parametrize(
    "text",
    ["{}", "[]", "null", '{"title":"Metadata only"}', '{"tabs":[{}]}', '{"error":{"message":"PRIVATE"}}', "PRIVATE"],
)
def test_docs_malformed_or_metadata_only_is_not_empty_success(tmp_path: Path, text: str) -> None:
    result = run_helper(tmp_path, "docs_text", text)
    assert result.returncode == 1
    assert result.stdout == ""
    assert "PRIVATE" not in result.stderr


@pytest.mark.parametrize(
    ("text", "recovery"),
    [
        ('{"error":{"message":"PRIVATE"}}', "docs_text: Expected a successful documents.get object.\n"),
        ('{"title":"PRIVATE"}', "docs_text: No body or tabs; fetch documents.get with includeTabsContent=true.\n"),
        (
            '{"tabs":[{"tabProperties":{"tabId":"t1","title":"PRIVATE"},"documentTab":{}}]}',
            "docs_text: Body missing; fetch document content without a metadata-only field mask.\n",
        ),
        ('{"title":"PRIVATE"', "docs_text: Invalid JSON near character 18.\n"),
        (
            '{"tabs":[{"title":"PRIVATE"}]}',
            "docs_text: Invalid or unreadable Docs input (KeyError); fetch full tab content.\n",
        ),
    ],
)
def test_docs_failure_prints_its_specific_recovery_without_content(tmp_path: Path, text: str, recovery: str) -> None:
    result = run_helper(tmp_path, "docs_text", text)
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == recovery


def test_docs_undecodable_input_keeps_its_bytes_off_stderr(tmp_path: Path) -> None:
    # A UnicodeDecodeError is a ValueError whose text quotes the offending byte: only its type is printed.
    source = tmp_path / "document.json"
    source.write_bytes(b'{"title":"PRIVATE \xe9"}')
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "docs_text.py"), str(source)],
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 1
    assert result.stderr == (
        "docs_text: Invalid or unreadable Docs input (UnicodeDecodeError); fetch full tab content.\n"
    )


def test_pages_undecodable_input_keeps_its_bytes_off_stderr(tmp_path: Path) -> None:
    source = tmp_path / "pages.json"
    source.write_bytes(b'{"files":[{"name":"PRIVATE \xe9"}]}')
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "pages.py"), str(source), "--items", "files"],
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 1
    assert result.stderr == "pages: Input is not valid UTF-8; retain only UTF-8 gws stdout.\n"


def test_drive_upload_dry_run_and_validation(tmp_path: Path) -> None:
    report = tmp_path / "report.html"
    report.write_text("<h1>Hello</h1>\n", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "drive_upload.py"),
            str(report),
            "--drive-folder",
            "folder_12345678",
            "--target-mime",
            "application/vnd.google-apps.document",
            "--dry-run",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    plan = json.loads(result.stdout)
    assert plan["ok"] is True
    assert plan["dry_run"] is True
    assert plan["remote_name"] == "report"
    assert plan["upload_content_type"] == "text/html"
    assert plan["target_mime"] == "application/vnd.google-apps.document"

    bad = subprocess.run(
        [sys.executable, str(SCRIPTS / "drive_upload.py"), str(report), "--drive-folder", "bad/id", "--dry-run"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert bad.returncode == 1
    assert "Invalid --drive-folder" in bad.stderr


def test_drive_upload_create_and_verify_with_mocked_gws(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import hashlib

    mod = load_script("drive_upload", SCRIPTS / "drive_upload.py")

    pdf = tmp_path / "deck.pdf"
    pdf.write_bytes(b"%PDF-1.7\nhello\n")
    expected_md5 = hashlib.md5(pdf.read_bytes(), usedforsecurity=False).hexdigest()

    calls: list[list[str]] = []

    def fake_run_gws(args: list[str], *, cwd: Path) -> dict[str, object]:
        calls.append(args)
        assert (cwd / "upload.pdf").is_file()
        if args[:3] == ["drive", "files", "list"]:
            return {"files": []}
        if args[:3] == ["drive", "files", "create"]:
            return {"id": "file_12345678"}
        if args[:3] == ["drive", "files", "get"]:
            return {
                "id": "file_12345678",
                "name": "deck.pdf",
                "mimeType": "application/pdf",
                "webViewLink": "https://drive.google.com/file/d/file_12345678/view",
                "trashed": False,
                "md5Checksum": expected_md5,
                "size": str(pdf.stat().st_size),
            }
        raise AssertionError(f"Unexpected gws call: {args}")

    monkeypatch.setattr(mod, "run_gws", fake_run_gws)
    result = mod.upload_file(pdf, drive_folder="folder_12345678")
    assert result["ok"] is True
    assert result["action"] == "created"
    assert result["id"] == "file_12345678"
    assert len(calls) == 3

    # --file-id without --name preserves the remote filename (omits --json metadata patch).
    calls.clear()

    def fake_update_gws(args: list[str], *, cwd: Path) -> dict[str, object]:
        calls.append(args)
        assert (cwd / "upload.pdf").is_file()
        if args[:3] == ["drive", "files", "update"]:
            assert "--json" not in args
            return {"id": "existing_12345678"}
        return {
            "id": "existing_12345678",
            "name": "Original Remote Title.pdf",
            "mimeType": "application/pdf",
            "trashed": False,
            "md5Checksum": expected_md5,
            "size": str(pdf.stat().st_size),
        }

    monkeypatch.setattr(mod, "run_gws", fake_update_gws)
    updated = mod.upload_file(pdf, file_id="existing_12345678")
    assert updated["action"] == "updated"
    assert updated["name"] == "Original Remote Title.pdf"

    # Existing .gdoc must never be overwritten via drive.files.update (drops comments/suggestions),
    # even when --target-mime is omitted.
    html = tmp_path / "memo.html"
    html.write_text("<h1>Memo</h1>\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"documents\.batchUpdate"):
        mod.upload_file(html, file_id="existing_12345678", target_mime=mod.GOOGLE_DOC_MIME)
    monkeypatch.setattr(
        mod,
        "run_gws",
        lambda _args, **_kw: {"id": "gdoc_12345678", "mimeType": mod.GOOGLE_DOC_MIME, "trashed": False},
    )
    with pytest.raises(ValueError, match=r"documents\.batchUpdate"):
        mod.upload_file(html, file_id="gdoc_12345678")
    monkeypatch.setattr(
        mod,
        "run_gws",
        lambda _args, **_kw: {"id": "trash_12345678", "mimeType": "text/markdown", "trashed": True},
    )
    with pytest.raises(ValueError, match="trashed"):
        mod.upload_file(html, file_id="trash_12345678")

    # --file-id with mismatched --target-mime must fail closed before calling drive.files.update.
    mismatch_calls: list[list[str]] = []

    def mismatch_gws(args: list[str], **_kw: object) -> dict[str, object]:
        mismatch_calls.append(args)
        return {"id": "pdf_12345678", "mimeType": "application/pdf", "trashed": False}

    monkeypatch.setattr(mod, "run_gws", mismatch_gws)
    with pytest.raises(ValueError, match="expected 'text/markdown'"):
        mod.upload_file(html, file_id="pdf_12345678", target_mime="text/markdown")
    assert [c[:3] for c in mismatch_calls] == [["drive", "files", "get"]]

    # Missing mimeType or Google-native target without --target-mime must also fail closed before update.
    monkeypatch.setattr(mod, "run_gws", lambda _args, **_kw: {"id": "nomime_1234", "trashed": False})
    with pytest.raises(RuntimeError, match="missing mimeType"):
        mod.upload_file(html, file_id="nomime_1234")
    monkeypatch.setattr(
        mod,
        "run_gws",
        lambda _args, **_kw: {
            "id": "slides_1234",
            "mimeType": "application/vnd.google-apps.presentation",
            "trashed": False,
        },
    )
    with pytest.raises(ValueError, match="Google-native"):
        mod.upload_file(html, file_id="slides_1234")
    monkeypatch.setattr(mod, "run_gws", lambda _args, **_kw: {"files": [{"id": "gdoc_12345678", "name": "memo"}]})
    with pytest.raises(ValueError, match=r"documents\.batchUpdate"):
        mod.upload_file(html, drive_folder="folder_12345678", target_mime=mod.GOOGLE_DOC_MIME)

    # Multiple same-named files in a folder fail closed instead of picking files[0].
    monkeypatch.setattr(
        mod,
        "run_gws",
        lambda _args, **_kw: {
            "files": [{"id": "a_12345678", "name": "deck.pdf"}, {"id": "b_12345678", "name": "deck.pdf"}]
        },
    )
    with pytest.raises(RuntimeError, match="Multiple Drive files"):
        mod.upload_file(pdf, drive_folder="folder_12345678")

    # Empty source file fails closed.
    empty = tmp_path / "empty.pdf"
    empty.write_bytes(b"")
    with pytest.raises(ValueError, match="non-empty"):
        mod.upload_file(empty, drive_folder="folder_12345678")

    # Fail closed on MD5 mismatch during read-back.
    def bad_md5_gws(args: list[str], *, cwd: Path) -> dict[str, object]:
        res = fake_run_gws(args, cwd=cwd)
        if args[:3] == ["drive", "files", "get"]:
            res["md5Checksum"] = "0" * 32
        return res

    monkeypatch.setattr(mod, "run_gws", bad_md5_gws)
    with pytest.raises(RuntimeError, match="MD5 mismatch"):
        mod.upload_file(pdf, drive_folder="folder_12345678")
