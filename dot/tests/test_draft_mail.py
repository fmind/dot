"""Exercise the Gmail rich HTML multipart/alternative draft builder (draft_email.py)."""

from __future__ import annotations

import base64
import importlib.util
import json
import re
from email import message_from_bytes
from email.message import EmailMessage
from email.policy import default as default_policy
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "skills/draft-mail/scripts/draft_email.py"

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
    spec = importlib.util.spec_from_file_location("draft_email", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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

    def fake_run_gws(args: list[str], context: str) -> dict[str, Any]:
        gws_calls.append(args)
        if args[:5] == ["gmail", "users", "settings", "sendAs", "list"]:
            return {"sendAs": [{"sendAsEmail": "github@fmind.dev", "isDefault": True}]}
        if args[:5] == ["gmail", "users", "settings", "sendAs", "get"]:
            params = json.loads(args[args.index("--params") + 1])
            assert params == {"userId": "me", "sendAsEmail": "github@fmind.dev"}
            return SAMPLE_SEND_AS
        if args[:4] == ["gmail", "users", "drafts", "create"]:
            return {"id": "r-draft-101"}
        if args[:4] == ["gmail", "users", "drafts", "update"]:
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
