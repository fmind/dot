"""Exercise the Gmail rich HTML multipart/alternative draft builder (draft_email.py)."""

from __future__ import annotations

import base64
import json
import os
import re
from email import message_from_bytes
from email.message import EmailMessage
from email.policy import default as default_policy
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from repo_helpers import ROOT, load_script, native_binary

SCRIPT = ROOT / "skills/draft/references/mail/scripts/draft_email.py"

SAMPLE_SEND_AS: dict[str, Any] = {
    "sendAsEmail": "github@fmind.dev",
    "displayName": "Médéric HURIER (Fmind)",
    "isDefault": True,
    "signature": '<div dir="ltr"><b>Médéric HURIER (Fmind)</b><br>AI Architect - Fmind</div>',
}


def _b64url(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


def _decode_raw_mime(raw_b64: str) -> EmailMessage:
    padded = raw_b64 + "=" * (-len(raw_b64) % 4)
    msg = message_from_bytes(base64.urlsafe_b64decode(padded), policy=default_policy)
    assert isinstance(msg, EmailMessage)
    return msg


@pytest.fixture
def mod() -> ModuleType:
    return load_script("draft_email", SCRIPT)


def test_compose_new_thread_builds_multipart_alternative_and_injects_signature(mod: ModuleType) -> None:
    body_html = (
        "<p>Bonjour Alice,</p>"
        "<p><strong>We can enable the new rule on Monday.</strong></p>"
        '<ul><li><strong>Scope:</strong> production API gateway (<a href="https://example.com/pr/42">PR #42</a>).</li></ul>'
    )
    built = mod.compose_draft_payload(
        body_html,
        send_as=SAMPLE_SEND_AS,
        to_flags=["Alice Martin <alice@example.com>"],
        cc_flags=["team@fmind.ai"],
        bcc_flags=[],
        remove_flags=[],
        subject="Action required: API gateway rule",
    )

    assert "threadId" not in built["draft"]["message"]
    assert built["summary"]["mimeType"] == "multipart/alternative"
    assert built["summary"]["hasSignature"] is True
    assert built["summary"]["hasQuote"] is False

    mime_msg = _decode_raw_mime(built["draft"]["message"]["raw"])
    assert mime_msg.get_content_type() == "multipart/alternative"
    assert "github@fmind.dev" in mime_msg["From"]
    assert mime_msg["To"] == "Alice Martin <alice@example.com>"
    assert mime_msg["Cc"] == "team@fmind.ai"
    assert mime_msg["Subject"] == "Action required: API gateway rule"

    parts = list(mime_msg.iter_parts())
    assert [p.get_content_type() for p in parts] == ["text/plain", "text/html"]

    plain_body = parts[0].get_content().replace("\r\n", "\n")
    html_body = parts[1].get_content()

    assert "Bonjour Alice," in plain_body
    assert "https://example.com/pr/42" in plain_body
    assert "-- \nMédéric HURIER (Fmind)\nAI Architect - Fmind" in plain_body

    assert html_body.startswith('<div dir="ltr">')
    assert '<div dir="ltr" class="gmail_signature" data-smartmail="gmail_signature">' in html_body
    assert SAMPLE_SEND_AS["signature"] in html_body


def test_compose_reply_preserves_thread_headers_recipients_and_collapsible_quote(mod: ModuleType) -> None:
    parent_html = '<div dir="ltr"><p>Can we enable the rule on Monday?</p></div>'
    parent_text = "Can we enable the rule on Monday?"
    parent_msg: dict[str, Any] = {
        "id": "msg_parent_1",
        "threadId": "thread_abc_123",
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [
                {"name": "From", "value": "Alice Martin <alice@example.com>"},
                {
                    "name": "To",
                    "value": "github@fmind.dev, Bob Leroy <bob@example.com>",
                },
                {"name": "Cc", "value": "carol@example.com, dropme@example.com"},
                {"name": "Subject", "value": "API gateway rule"},
                {"name": "Date", "value": "Thu, 29 Oct 2026 14:00:00 +0100"},
                {"name": "Message-ID", "value": "<msg-2@mail.example.com>"},
                {"name": "References", "value": "<msg-1@mail.example.com>"},
            ],
            "parts": [
                {"mimeType": "text/plain", "body": {"data": _b64url(parent_text)}},
                {"mimeType": "text/html", "body": {"data": _b64url(parent_html)}},
            ],
        },
    }

    built = mod.compose_draft_payload(
        "<p>Yes, Monday at 09:00 CET works for us.</p>",
        send_as=SAMPLE_SEND_AS,
        to_flags=[],
        cc_flags=["team@fmind.ai"],
        bcc_flags=[],
        remove_flags=["dropme@example.com"],
        parent_msg=parent_msg,
        reply_all=True,
    )

    assert built["draft"]["message"]["threadId"] == "thread_abc_123"
    summary = built["summary"]
    assert summary["subject"] == "Re: API gateway rule"
    assert summary["inReplyTo"] == "<msg-2@mail.example.com>"
    assert summary["references"] == "<msg-1@mail.example.com> <msg-2@mail.example.com>"
    assert summary["to"] == ["Alice Martin <alice@example.com>"]
    assert summary["cc"] == [
        "Bob Leroy <bob@example.com>",
        "carol@example.com",
        "team@fmind.ai",
    ]
    assert summary["hasSignature"] is True
    assert summary["hasQuote"] is True

    mime_msg = _decode_raw_mime(built["draft"]["message"]["raw"])
    assert mime_msg["In-Reply-To"] == "<msg-2@mail.example.com>"
    assert mime_msg["References"] == "<msg-1@mail.example.com> <msg-2@mail.example.com>"
    assert mime_msg["Subject"] == "Re: API gateway rule"

    parts = list(mime_msg.iter_parts())
    plain_body = parts[0].get_content()
    html_body = parts[1].get_content()

    sig_pos = html_body.index('class="gmail_signature"')
    quote_pos = html_body.index('<div class="gmail_quote gmail_quote_container">')
    assert sig_pos < quote_pos, "Quoted history must be placed below the signature"
    assert (
        '<blockquote class="gmail_quote" '
        'style="margin:0px 0px 0px 0.8ex;border-left:1px solid rgb(204,204,204);padding-left:1ex">'
    ) in html_body
    assert "<p>Can we enable the rule on Monday?</p>" in html_body
    assert "mailto:alice@example.com" in html_body
    assert "> Can we enable the rule on Monday?" in plain_body


def test_unwrap_outer_dir_ltr_preserves_multi_block_siblings(mod: ModuleType) -> None:
    fragment = '<div dir="ltr"><p>First block</p></div><div><p>Second block</p></div>'
    built = mod.compose_draft_payload(
        fragment,
        send_as=SAMPLE_SEND_AS,
        to_flags=["alice@example.com"],
        cc_flags=[],
        bcc_flags=[],
        remove_flags=[],
        subject="Multi-block test",
    )
    mime_msg = _decode_raw_mime(built["draft"]["message"]["raw"])
    html_body = list(mime_msg.iter_parts())[1].get_content()
    assert fragment in html_body


@pytest.mark.parametrize(
    ("bad_body", "expected_error"),
    [
        ("   ", "empty"),
        ("Bonjour Alice,\n\nPlain text without HTML tags.", "Plain-text body rejected"),
        ("<p>Bonjour</p>\n# Markdown Heading\n<p>Text</p>", "Raw Markdown heading"),
        ("<p>Bonjour **Alice**,</p>", "Raw Markdown **bold**"),
        ("<p>See [PR #42](https://example.com/pr/42) for details.</p>", "Raw Markdown [text](url)"),
        ("<p>Snippet:</p>\n```python\npass\n```", "Raw Markdown code fence"),
        ("<p>Checked `loader.py` in staging.</p>", "Raw Markdown `inline code`"),
    ],
)
def test_validate_html_fragment_rejects_plain_text_and_raw_markdown(
    mod: ModuleType,
    bad_body: str,
    expected_error: str,
) -> None:
    with pytest.raises(ValueError, match=re.escape(expected_error)):
        mod.validate_html_fragment(bad_body)


def test_validate_html_fragment_allows_markdown_tokens_inside_code_tags(mod: ModuleType) -> None:
    fragment = "<p>Run <code>uv run **bold** [x](https://example.com)</code>:</p><pre><code># comment\n```</code></pre>"
    assert mod.validate_html_fragment(fragment) == fragment


def test_cli_live_gws_workflow_fetches_sendas_and_creates_or_updates_draft(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    body_file = tmp_path / "body.html"
    body_file.write_text("<p>Bonjour,</p><p><strong>Update ready.</strong></p>", encoding="utf-8")
    attach_file = tmp_path / "report.txt"
    attach_file.write_text("attachment content\n", encoding="utf-8")

    gws_calls: list[list[str]] = []

    def fake_run_gws(args: list[str], context: str, *, cwd: Path | None = None) -> dict[str, Any]:
        gws_calls.append(args)
        if args[:5] == ["gmail", "users", "settings", "sendAs", "list"]:
            return {"sendAs": [{"sendAsEmail": "github@fmind.dev", "isDefault": True}]}
        if args[:5] == ["gmail", "users", "settings", "sendAs", "get"]:
            params = json.loads(args[args.index("--params") + 1])
            assert params == {"userId": "me", "sendAsEmail": "github@fmind.dev"}
            return SAMPLE_SEND_AS
        if args[:4] in (["gmail", "users", "drafts", "create"], ["gmail", "users", "drafts", "update"]):
            # gws rejects --upload paths outside its working directory; staging stays out of the checkout.
            name = args[args.index("--upload") + 1]
            assert cwd is not None
            assert "/" not in name
            assert (cwd / name).is_file()
            assert not cwd.resolve().is_relative_to(Path.cwd().resolve())
            return {"id": "r-draft-101"}
        if args[:4] == ["gmail", "users", "drafts", "get"]:
            return {
                "id": "r-draft-101",
                "message": {
                    "id": "msg-101",
                    "threadId": "thread-101",
                    "payload": {
                        "mimeType": "multipart/mixed",
                        "parts": [
                            {"mimeType": "multipart/alternative"},
                            {"mimeType": "text/plain"},
                        ],
                    },
                },
            }
        raise AssertionError(f"Unexpected gws call ({context}): {args}")

    monkeypatch.setattr(mod, "_run_gws", fake_run_gws)

    rc = mod.main(
        [
            str(body_file),
            "--to",
            "alice@example.com",
            "--cc",
            "team@fmind.ai",
            "--subject",
            "Weekly status",
            "--attach",
            str(attach_file),
        ]
    )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["draftId"] == "r-draft-101"
    assert out["hasSignature"] is True
    assert [c[:5] for c in gws_calls] == [
        ["gmail", "users", "settings", "sendAs", "list"],
        ["gmail", "users", "settings", "sendAs", "get"],
        ["gmail", "users", "drafts", "create", "--params"],
        ["gmail", "users", "drafts", "get", "--params"],
    ]

    # Test updating an existing draft in place (--draft-id) with explicit --from
    gws_calls.clear()
    rc_update = mod.main(
        [
            str(body_file),
            "--draft-id",
            "r-draft-101",
            "--from",
            "github@fmind.dev",
            "--to",
            "alice@example.com",
            "--subject",
            "Weekly status (revised)",
        ]
    )
    assert rc_update == 0
    assert [c[:5] for c in gws_calls] == [
        ["gmail", "users", "settings", "sendAs", "get"],
        ["gmail", "users", "drafts", "update", "--params"],
        ["gmail", "users", "drafts", "get", "--params"],
    ]


PARENT_MESSAGE: dict[str, Any] = {
    "id": "msg_parent_1",
    "threadId": "thread_abc_123",
    "payload": {
        "mimeType": "text/plain",
        "headers": [
            {"name": "From", "value": "Alice Martin <alice@example.com>"},
            {"name": "To", "value": "github@fmind.dev"},
            {"name": "Subject", "value": "API gateway rule"},
            {"name": "Message-ID", "value": "<msg-2@mail.example.com>"},
        ],
        "body": {"data": _b64url("Can we enable the rule on Monday?")},
    },
}


def _stub_gws(
    mod: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    *,
    draft: dict[str, Any] | None = None,
    readback_error: str | None = None,
) -> list[tuple[str, Path]]:
    """Replace _run_gws with canned Gmail answers; record each call's context and working directory."""
    calls: list[tuple[str, Path]] = []

    def fake_run_gws(args: list[str], context: str, *, cwd: Path) -> dict[str, Any]:
        calls.append((context, cwd))
        assert cwd.is_dir()
        if context == "sendAs.list":
            return {"sendAs": [{"sendAsEmail": "github@fmind.dev", "isDefault": True}]}
        if context == "sendAs.get":
            return SAMPLE_SEND_AS
        if context == "messages.get":
            return PARENT_MESSAGE
        if context == "drafts.create":
            assert (cwd / args[args.index("--upload") + 1]).is_file()
            return {"id": "r-draft-202"} if draft is None else draft
        if context == "drafts.get":
            if readback_error:
                raise RuntimeError(readback_error)
            return {"id": "r-draft-202", "message": {"id": "msg-202", "threadId": "thread_abc_123"}}
        raise AssertionError(f"Unexpected gws call ({context}): {args}")

    monkeypatch.setattr(mod, "_run_gws", fake_run_gws)
    return calls


def test_cli_runs_every_gws_call_from_one_private_directory(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # gws loads a `.env` from its working directory upward: one directory keeps one account for the whole run.
    body_file = tmp_path / "body.html"
    body_file.write_text("<p>Yes, Monday works.</p>", encoding="utf-8")
    calls = _stub_gws(mod, monkeypatch)

    assert mod.main([str(body_file), "--reply-to", "msg_parent_1"]) == 0
    assert json.loads(capsys.readouterr().out)["draftId"] == "r-draft-202"
    assert [context for context, _ in calls] == [
        "sendAs.list",
        "sendAs.get",
        "messages.get",
        "drafts.create",
        "drafts.get",
    ]
    directories = {cwd for _, cwd in calls}
    assert len(directories) == 1
    (directory,) = directories
    assert not directory.resolve().is_relative_to(Path.cwd().resolve())
    assert not directory.exists(), "the private staging directory is removed after the run"


def test_cli_names_the_saved_draft_when_the_read_back_fails(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    body_file = tmp_path / "body.html"
    body_file.write_text("<p>PRIVATE-BODY</p>", encoding="utf-8")
    calls = _stub_gws(mod, monkeypatch, readback_error="drafts.get failed: HTTP request failed")

    assert mod.main([str(body_file), "--to", "alice@example.com", "--subject", "Status"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "draft r-draft-202 was saved" in captured.err
    assert "rerun with --draft-id r-draft-202" in captured.err
    assert "PRIVATE-BODY" not in captured.err
    assert [context for context, _ in calls].count("drafts.create") == 1


def test_cli_asks_for_the_draft_id_when_create_returns_none(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    body_file = tmp_path / "body.html"
    body_file.write_text("<p>PRIVATE-BODY</p>", encoding="utf-8")
    calls = _stub_gws(mod, monkeypatch, draft={})

    assert mod.main([str(body_file), "--to", "alice@example.com", "--subject", "Status"]) == 1
    captured = capsys.readouterr()
    assert "returned no draft id" in captured.err
    assert "gws gmail users drafts list" in captured.err
    assert "--draft-id" in captured.err
    assert "PRIVATE-BODY" not in captured.err
    assert "drafts.get" not in [context for context, _ in calls]


def test_compose_accepts_mark_and_hr_visual_primitives(mod: ModuleType) -> None:
    body_html = (
        '<p>Decision: <mark style="background:#CEEAD6;color:#0D652D;">Approve Provider B</mark></p>'
        "<hr />"
        "<p>Next check-in: Friday 10:00 CET.</p>"
    )
    built = mod.compose_draft_payload(
        body_html,
        send_as=SAMPLE_SEND_AS,
        to_flags=["Alice Martin <alice@example.com>"],
        cc_flags=[],
        bcc_flags=[],
        remove_flags=[],
        subject="Decision: Provider B",
    )
    mime_msg = _decode_raw_mime(built["draft"]["message"]["raw"])
    plain_body = next(p for p in mime_msg.iter_parts() if p.get_content_type() == "text/plain").get_content()
    assert "Approve Provider B" in plain_body
    assert "\n---\n" in plain_body.replace("\r\n", "\n")


def test_cli_rejects_local_validation_errors_before_calling_gws(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls = _stub_gws(mod, monkeypatch)
    plain = tmp_path / "plain.txt"
    plain.write_text("Plain body without HTML.", encoding="utf-8")
    assert mod.main([str(plain), "--to", "alice@example.com", "--subject", "Hi"]) == 1
    assert "Plain-text body rejected" in capsys.readouterr().err

    html = tmp_path / "ok.html"
    html.write_text("<p>Hi</p>", encoding="utf-8")
    assert mod.main([str(html), "--to", "alice@example.com"]) == 1
    assert "--subject is required" in capsys.readouterr().err
    assert mod.main([str(html), "--subject", "Hi"]) == 1
    assert "--to is required" in capsys.readouterr().err
    assert (
        mod.main([str(html), "--to", "alice@example.com", "--subject", "Hi", "--attach", str(tmp_path / "none.pdf")])
        == 1
    )
    assert "Attachment not found" in capsys.readouterr().err
    assert mod.main([str(html), "--to", "alice@example.com", "--subject", "Hi", "--draft-id", "   "]) == 1
    assert "--draft-id" in capsys.readouterr().err
    assert mod.main([str(html), "--reply-to", "   "]) == 1
    assert "--reply-to" in capsys.readouterr().err
    assert mod.main([str(html), "--to", "alice@example.com", "--subject", "Hi", "--from", "   "]) == 1
    assert "--from" in capsys.readouterr().err
    assert calls == []


def test_cli_rejects_malformed_gmail_identifiers_before_calling_gws(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    gws_calls: list[list[str]] = []
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/usr/bin/gws" if name == "gws" else None)
    monkeypatch.setattr(
        mod.subprocess,
        "run",
        lambda cmd, **_kwargs: gws_calls.append(list(cmd)),
    )

    html = tmp_path / "ok.html"
    html.write_text("<p>Hi</p>", encoding="utf-8")

    for bad_draft_id in ("bad?id=1", "../x"):
        assert (
            mod.main(
                [
                    str(html),
                    "--to",
                    "alice@example.com",
                    "--subject",
                    "Hi",
                    "--draft-id",
                    bad_draft_id,
                ]
            )
            == 1
        )
        assert "--draft-id" in capsys.readouterr().err

    assert mod.main([str(html), "--reply-to", "msg#frag"]) == 1
    assert "--reply-to" in capsys.readouterr().err
    assert gws_calls == []


def test_cli_fails_on_gws_error_payload_or_missing_updated_draft_id(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    html = tmp_path / "ok.html"
    html.write_text("<p>Hi</p>", encoding="utf-8")

    monkeypatch.setattr(mod.shutil, "which", lambda name: "/usr/bin/gws" if name == "gws" else None)

    def _dispatch_settings(cmd: list[str]) -> str | None:
        if cmd[1:6] == ["gmail", "users", "settings", "sendAs", "list"]:
            return json.dumps({"sendAs": [{"sendAsEmail": "github@fmind.dev", "isDefault": True}]})
        if cmd[1:6] == ["gmail", "users", "settings", "sendAs", "get"]:
            return json.dumps(SAMPLE_SEND_AS)
        return None

    # (a) gws exits 0 with a JSON error envelope on drafts.update
    error_calls: list[list[str]] = []

    def _run_error(cmd: list[str], **_kwargs: object) -> object:
        error_calls.append(list(cmd))
        settings_payload = _dispatch_settings(cmd)
        if settings_payload is not None:
            return mod.subprocess.CompletedProcess(args=cmd, returncode=0, stdout=settings_payload, stderr="")
        return mod.subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout='{"error": {"code": 403, "message": "Insufficient Permission"}}',
            stderr="",
        )

    monkeypatch.setattr(mod.subprocess, "run", _run_error)
    rc = mod.main(
        [
            str(html),
            "--to",
            "alice@example.com",
            "--subject",
            "Hi",
            "--draft-id",
            "r-draft-101",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 1
    assert "Google API error" in captured.err
    assert "Insufficient Permission" in captured.err
    assert "updated" not in captured.out.lower()
    assert [c[1:5] for c in error_calls] == [
        ["gmail", "users", "settings", "sendAs"],
        ["gmail", "users", "settings", "sendAs"],
        ["gmail", "users", "drafts", "update"],
    ]

    # (b) drafts.update exits 0 with {} when --draft-id is passed
    empty_calls: list[list[str]] = []

    def _run_empty(cmd: list[str], **_kwargs: object) -> object:
        empty_calls.append(list(cmd))
        settings_payload = _dispatch_settings(cmd)
        if settings_payload is not None:
            return mod.subprocess.CompletedProcess(args=cmd, returncode=0, stdout=settings_payload, stderr="")
        return mod.subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="{}",
            stderr="",
        )

    monkeypatch.setattr(mod.subprocess, "run", _run_empty)
    rc_empty = mod.main(
        [
            str(html),
            "--to",
            "alice@example.com",
            "--subject",
            "Hi",
            "--draft-id",
            "r-draft-101",
        ]
    )
    captured_empty = capsys.readouterr()
    assert rc_empty == 1
    assert "returned no draft id" in captured_empty.err
    assert [c[1:5] for c in empty_calls] == [
        ["gmail", "users", "settings", "sendAs"],
        ["gmail", "users", "settings", "sendAs"],
        ["gmail", "users", "drafts", "update"],
    ]


def test_cli_gws_stdout_banner_and_malformed_or_truncated_json(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    html = tmp_path / "ok.html"
    html.write_text("<p>Hi</p>", encoding="utf-8")
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/usr/bin/gws" if name == "gws" else None)
    created_payload = json.dumps({"id": "draft_1"})
    active_payload = [f"[INFO] created{chr(10)}{created_payload}{chr(10)}"]

    def _fake(cmd: list[str], **_kwargs: object) -> object:
        if cmd[1:6] == ["gmail", "users", "settings", "sendAs", "list"]:
            body = json.dumps({"sendAs": [{"sendAsEmail": "github@fmind.dev", "isDefault": True}]})
            return mod.subprocess.CompletedProcess(
                cmd, 0, f"[INFO] using {{keyring}} backend{chr(10)}{body}{chr(10)}", ""
            )
        if cmd[1:6] == ["gmail", "users", "settings", "sendAs", "get"]:
            return mod.subprocess.CompletedProcess(cmd, 0, json.dumps(SAMPLE_SEND_AS), "")
        return mod.subprocess.CompletedProcess(cmd, 0, active_payload[0], "")

    monkeypatch.setattr(mod.subprocess, "run", _fake)
    assert mod.main([str(html), "--to", "alice@example.com", "--subject", "Hi"]) == 0
    assert "draft_1" in capsys.readouterr().out

    for bad_stdout in (
        "",
        "[]",
        "Error [503]",
        '{"error": {"code": 403}',
        f'{{"error": {{{chr(10)}{{"code": 403}}',
    ):
        active_payload[0] = bad_stdout
        assert mod.main([str(html), "--to", "alice@example.com", "--subject", "Hi"]) == 1
        assert "expected" in capsys.readouterr().err


def test_cli_vale_blocks_errors_and_surfaces_advisory_warnings(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    vale_bin = native_binary("vale")
    if vale_bin is None:
        if os.environ.get("CI"):
            pytest.fail("Vale binary must be installed in CI via mise.toml")
        pytest.skip("Vale binary is required for draft_email prose gate verification")
    monkeypatch.setenv("PATH", f"{vale_bin.parent}{os.pathsep}{os.environ.get('PATH', '')}")

    # Point global config fallback to the repository's Vale config.
    monkeypatch.chdir(tmp_path)
    tmp_path.chmod(0o700)
    vale_ini = tmp_path / ".vale.ini"
    vale_ini.write_text(
        f"StylesPath = {Path(__file__).resolve().parents[1] / 'dot_config/vale/styles'}\n"
        "MinAlertLevel = warning\nIgnoredScopes = code, tt\nSkippedScopes = script, style, pre, figure\n"
        "[*.{md,mdx,txt,html}]\nBasedOnStyles = Fmind\n",
        encoding="utf-8",
    )
    vale_ini.chmod(0o600)

    slop_html = tmp_path / "slop.html"
    slop_html.write_text("<p>We delve into updates &mdash; ready now.</p>", encoding="utf-8")
    monkeypatch.setattr(mod, "_run_gws", lambda *_a, **_kw: (_ for _ in ()).throw(AssertionError("gws called")))
    assert mod.main([str(slop_html), "--to", "alice@example.com", "--subject", "Update", "--dry-run"]) == 1
    err = capsys.readouterr().err
    assert "Fmind.SlopWords" in err
    assert "Fmind.EmDash" in err

    warn_html = tmp_path / "warn.html"
    warn_html.write_text("<p>We leverage seamless failover in order to stay online.</p>", encoding="utf-8")
    monkeypatch.setattr(mod, "resolve_send_as", lambda *_a, **_kw: SAMPLE_SEND_AS)
    assert mod.main([str(warn_html), "--to", "alice@example.com", "--subject", "Update", "--dry-run"]) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert any("Fmind.SlopStyle" in item for item in payload["proseWarnings"])
    assert any("Fmind.Wordiness" in item for item in payload["proseWarnings"])
    assert "draft_email warning:" in captured.err


def test_recipient_specials_crlf_quotes_and_vale_hardening(
    mod: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import subprocess
    import sys

    # RFC 5322 specials `.[]` in display names must be quoted so SMTP headers stay defect-free.
    built = mod.compose_draft_payload(
        "<p>Hello team.</p>",
        send_as=SAMPLE_SEND_AS,
        to_flags=['"Team [FR]" <team@example.com>', '"Dr. Smith" <dr@example.com>'],
        cc_flags=[],
        bcc_flags=[],
        remove_flags=[],
        subject="Specials test",
    )
    mime_msg = _decode_raw_mime(built["draft"]["message"]["raw"])
    assert not mime_msg["To"].defects
    assert "team@example.com" in mime_msg["To"]
    assert "dr@example.com" in mime_msg["To"]

    # CRLF plain-text parent quote converts cleanly without residual \r before <br>.
    parent_crlf: dict[str, Any] = {
        "id": "m1",
        "threadId": "t1",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "Alice <alice@example.com>"},
                {"name": "To", "value": "github@fmind.dev"},
                {"name": "Subject", "value": "CRLF"},
                {"name": "Message-ID", "value": "<m1@example.com>"},
            ],
            "body": {"data": _b64url("Line 1\r\nLine 2\r\n")},
        },
    }
    ctx = mod.extract_reply_context(parent_crlf)
    assert "\r" not in ctx["quotedHtml"]
    assert "Line 1<br>Line 2" in ctx["quotedHtml"]

    # Invalid recipient flags (missing '@', empty angle addr, double '@', invalid --from) fail before calling gws.
    html_file = tmp_path / "body.html"
    html_file.write_text("<p>Hello.</p>", encoding="utf-8")
    for bad_argv in (
        [str(html_file), "--to", "not-an-email", "--subject", "Hi"],
        [str(html_file), "--to", "alice@example.com", "--cc", "Bob <>", "--subject", "Hi"],
        [str(html_file), "--to", "a@b@c", "--subject", "Hi"],
        [str(html_file), "--to", "alice@example.com", "--from", "@", "--subject", "Hi"],
    ):
        assert mod.main(bad_argv) == 1
        assert "valid email address" in capsys.readouterr().err

    # Vale config discovery refuses world/group-writable parent dirs; exit-1 without findings and timeout fail closed.
    mail_mime = sys.modules["mail_mime"]
    world_dir = tmp_path / "world"
    world_dir.mkdir()
    world_cfg = world_dir / ".vale.ini"
    world_cfg.write_text("MinAlertLevel = error\n", encoding="utf-8")
    world_cfg.chmod(0o600)
    for bad_mode in (0o777, 0o775):
        world_dir.chmod(bad_mode)
        try:
            assert mail_mime._is_trusted_vale_config(world_cfg) is False  # noqa: SLF001
        finally:
            world_dir.chmod(0o700)

    tmp_path.chmod(0o700)
    safe_cfg = tmp_path / ".vale.ini"
    safe_cfg.write_text("MinAlertLevel = error\n", encoding="utf-8")
    safe_cfg.chmod(0o600)
    monkeypatch.setattr(mail_mime.shutil, "which", lambda name: "/bin/vale" if name == "vale" else None)
    monkeypatch.setattr(
        mail_mime.subprocess,
        "run",
        lambda *_a, **_kw: subprocess.CompletedProcess(["vale"], 1, stdout="", stderr="config error"),
    )
    with pytest.raises(RuntimeError, match="vale failed"):
        mail_mime.check_prose_with_vale("<p>hi</p>", cwd=tmp_path)

    monkeypatch.setattr(
        mail_mime.subprocess,
        "run",
        lambda *_a, **_kw: subprocess.CompletedProcess(["vale"], 1, stdout="{}", stderr=""),
    )
    with pytest.raises(RuntimeError, match="without error findings"):
        mail_mime.check_prose_with_vale("<p>hi</p>", cwd=tmp_path)

    monkeypatch.setattr(
        mail_mime.subprocess,
        "run",
        lambda *_a, **_kw: (_ for _ in ()).throw(subprocess.TimeoutExpired(["vale"], 20)),
    )
    with pytest.raises(RuntimeError, match="vale timed out"):
        mail_mime.check_prose_with_vale("<p>hi</p>", cwd=tmp_path)

    # Untrusted parent HTML in replies must strip scripts/handlers and balance breakout tags.
    evil_parent: dict[str, Any] = {
        "id": "m2",
        "threadId": "t2",
        "payload": {
            "mimeType": "text/html",
            "headers": [
                {"name": "From", "value": "Mallory <mallory@example.com>"},
                {"name": "To", "value": "github@fmind.dev"},
                {"name": "Subject", "value": "XSS"},
                {"name": "Message-ID", "value": "<m2@example.com>"},
            ],
            "body": {
                "data": _b64url(
                    '</blockquote></div><script>alert(1)</script><p onclick="evil()">Hi '
                    '<a href="javascript:alert(2)">click</a> <a href="https://example.com">ok</a>'
                )
            },
        },
    }
    evil_ctx = mod.extract_reply_context(evil_parent)
    assert "<script" not in evil_ctx["quotedHtml"].lower()
    assert "alert(1)" not in evil_ctx["quotedHtml"]
    assert "onclick" not in evil_ctx["quotedHtml"].lower()
    assert "javascript:" not in evil_ctx["quotedHtml"].lower()
    assert "</blockquote>" not in evil_ctx["quotedHtml"].lower()
    assert 'href="https://example.com"' in evil_ctx["quotedHtml"]
    assert evil_ctx["quotedHtml"].endswith("</p>")
