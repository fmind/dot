#!/usr/bin/env python3
"""Create or update a rich HTML multipart/alternative Gmail draft with sendAs signature and reply quoting."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

# Support `python3 -I` and direct `importlib.util.spec_from_file_location` loads without scripts/ on sys.path.
_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from mail_mime import (  # noqa: E402
    _dedupe_recipients,
    _format_recipient,
    _split_emails,
    _unwrap_outer_dir_ltr,
    build_quote_blocks,
    build_raw_mime_message,
    build_signature_blocks,
    check_prose_with_vale,
    decode_b64url_bytes,
    resolve_recipients,
)
from mail_mime import extract_reply_context as extract_reply_context  # noqa: E402
from mail_mime import html_to_text as html_to_text  # noqa: E402
from mail_mime import validate_html_fragment as validate_html_fragment  # noqa: E402

__all__ = [
    "compose_draft_payload",
    "extract_reply_context",
    "html_to_text",
    "main",
    "resolve_send_as",
    "validate_html_fragment",
]

GMAIL_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def _parse_json_stdout(stdout: str, context: str) -> dict[str, Any]:
    """Parse a JSON object from gws stdout, skipping any leading keyring status line."""
    out = stdout.strip()
    if not out:
        raise RuntimeError(f"{context}: expected JSON object on stdout.")
    decoder = json.JSONDecoder()
    data: Any = None
    found = False
    for pos, ch in enumerate(out):
        if (pos == 0 or out[pos - 1] == "\n") and ch == "{":
            try:
                data, end = decoder.raw_decode(out, pos)
            except json.JSONDecodeError:
                break
            if end == len(out) and isinstance(data, dict):
                found = True
            break
    if not found:
        raise RuntimeError(f"{context}: expected valid JSON object on stdout, got: {out[:200]}")
    if "error" in data:
        detail = json.dumps(data["error"], ensure_ascii=False)[:300]
        raise RuntimeError(f"{context}: Google API error: {detail}")
    return data


def _run_gws(args: list[str], context: str, *, cwd: Path) -> dict[str, Any]:
    """Execute a gws command in cwd and return its parsed JSON object, retrying once on transient HTTP errors."""
    gws_bin = shutil.which("gws")
    if not gws_bin:
        raise RuntimeError("`gws` not found in PATH; install @googleworkspace/cli (e.g. `mise install`).")
    last_msg = ""
    for attempt in range(2):
        try:
            proc = subprocess.run(  # noqa: S603 - fixed gws binary and validated arguments
                [gws_bin, *args],
                cwd=cwd,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"{context} timed out after 60 s; check its state before rerunning.") from exc
        if proc.returncode == 0:
            return _parse_json_stdout(proc.stdout, context)
        detail = (proc.stderr or proc.stdout).strip().splitlines()
        last_msg = detail[-1] if detail else f"exit code {proc.returncode}"
        # Never resend an uncertain create: it can duplicate the draft; list drafts and pass --draft-id.
        if attempt == 0 and "HTTP request failed" in last_msg and context != "drafts.create":
            time.sleep(1.0)
            continue
        break
    raise RuntimeError(f"{context} failed: {last_msg}")


def resolve_send_as(from_email: str | None, *, cwd: Path) -> dict[str, Any]:
    """Fetch the sender's sendAs profile and HTML signature from Gmail settings."""
    sender = (from_email or "").strip()
    if not sender:
        listing = _run_gws(
            ["gmail", "users", "settings", "sendAs", "list", "--params", '{"userId":"me"}', "--format", "json"],
            "sendAs.list",
            cwd=cwd,
        )
        entries = [e for e in (listing.get("sendAs") or []) if isinstance(e, dict)]
        chosen = next((e for e in entries if e.get("isDefault")), entries[0] if entries else None)
        if not chosen or not chosen.get("sendAsEmail"):
            raise RuntimeError("Could not resolve a default sendAs address for userId=me.")
        sender = str(chosen["sendAsEmail"]).strip()

    params = json.dumps({"userId": "me", "sendAsEmail": sender})
    return _run_gws(
        ["gmail", "users", "settings", "sendAs", "get", "--params", params, "--format", "json"],
        "sendAs.get",
        cwd=cwd,
    )


def compose_draft_payload(
    body_html: str,
    *,
    send_as: dict[str, Any],
    to_flags: list[str],
    cc_flags: list[str],
    bcc_flags: list[str],
    remove_flags: list[str],
    subject: str | None = None,
    parent_msg: dict[str, Any] | None = None,
    reply_all: bool = False,
    attachments: list[Path] | None = None,
) -> dict[str, Any]:
    """Construct the RFC 5322 multipart/alternative MIME message and Gmail draft payload."""
    validated_html = validate_html_fragment(body_html)
    core_html = _unwrap_outer_dir_ltr(validated_html)
    core_text = html_to_text(core_html)

    send_as_email = str(send_as.get("sendAsEmail") or "").strip()
    if not send_as_email:
        raise ValueError("sendAs profile is missing sendAsEmail.")
    display_name = str(send_as.get("displayName") or "").strip()
    from_header = _format_recipient(display_name, send_as_email)
    signature_html = str(send_as.get("signature") or "").strip()
    sig_block_html, sig_block_text = build_signature_blocks(signature_html)

    reply_ctx: dict[str, str] | None = None
    thread_id: str | None = None
    in_reply_to: str | None = None
    references: str | None = None
    quote_block_html = ""
    quote_block_text = ""

    if parent_msg is not None:
        reply_ctx = extract_reply_context(parent_msg)
        thread_id = reply_ctx["threadId"]
        in_reply_to = reply_ctx["messageId"]
        references = reply_ctx["references"]
        final_subject = (subject or "").strip() or reply_ctx["subject"]
        quote_block_html, quote_block_text = build_quote_blocks(reply_ctx)
    else:
        final_subject = (subject or "").strip()
        if not final_subject:
            raise ValueError("--subject is required when creating a new thread.")

    to_recipients, cc_recipients, bcc_recipients = resolve_recipients(
        send_as_email=send_as_email,
        to_flags=to_flags,
        cc_flags=cc_flags,
        bcc_flags=bcc_flags,
        remove_flags=remove_flags,
        reply_ctx=reply_ctx,
        reply_all=reply_all,
    )

    full_html = f'<div dir="ltr">{core_html}{sig_block_html}</div>{quote_block_html}'
    full_text = f"{core_text}{sig_block_text}{quote_block_text}\n"
    raw_b64, mime_type = build_raw_mime_message(
        from_header=from_header,
        to_recipients=to_recipients,
        cc_recipients=cc_recipients,
        bcc_recipients=bcc_recipients,
        subject=final_subject,
        full_text=full_text,
        full_html=full_html,
        in_reply_to=in_reply_to,
        references=references,
        attachments=attachments,
    )
    message_payload: dict[str, Any] = {"raw": raw_b64}
    if thread_id:
        message_payload["threadId"] = thread_id

    return {
        "draft": {"message": message_payload},
        "summary": {
            "from": from_header,
            "to": to_recipients,
            "cc": cc_recipients,
            "bcc": bcc_recipients,
            "subject": final_subject,
            "threadId": thread_id,
            "inReplyTo": in_reply_to,
            "references": references,
            "mimeType": mime_type,
            "hasSignature": bool(signature_html),
            "hasQuote": bool(quote_block_html),
        },
    }


def _clean_identifier(value: str | None, flag: str, description: str) -> str | None:
    """Validate and strip an optional Gmail draft or message identifier."""
    if value is None:
        return None
    cleaned = value.strip()
    if not GMAIL_ID_RE.fullmatch(cleaned):
        raise ValueError(f"{flag} must be a valid {description} (alphanumeric, '_', or '-').")
    return cleaned


def _build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser for Gmail draft composition."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False, suggest_on_error=True)
    parser.add_argument("input", help="Path to UTF-8 HTML body fragment file, or - for stdin")
    parser.add_argument("--to", action="append", default=[], help="To recipient(s), comma-separated")
    parser.add_argument("--cc", action="append", default=[], help="CC recipient(s), comma-separated")
    parser.add_argument("--bcc", action="append", default=[], help="BCC recipient(s), comma-separated")
    parser.add_argument("--remove", action="append", default=[], help="Exclude recipient(s) from To/CC")
    parser.add_argument("--subject", help="Email subject (required for new threads; defaults to Re: ... on replies)")
    parser.add_argument("--from", dest="from_email", help="Send-as email address (defaults to authenticated user)")
    parser.add_argument("--reply-to", dest="reply_to_id", help="Gmail message ID to reply to")
    parser.add_argument("--reply-all", action="store_true", help="Include original To/CC recipients on reply")
    parser.add_argument("--draft-id", help="Update an existing Gmail draft ID in place instead of creating a new one")
    parser.add_argument("-a", "--attach", action="append", type=Path, default=[], help="Attach a file (repeatable)")
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate and preview draft payload without calling Gmail write API"
    )
    return parser


def _validate_inputs(args: argparse.Namespace) -> str:
    """Read and validate the HTML body, IDs, sender, new-thread fields, and attachments before calling gws."""
    body_html = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
    validate_html_fragment(body_html)
    args.draft_id = _clean_identifier(args.draft_id, "--draft-id", "Gmail draft ID")
    args.reply_to_id = _clean_identifier(args.reply_to_id, "--reply-to", "Gmail message ID")
    if args.from_email is not None:
        cleaned_from = args.from_email.strip()
        if not cleaned_from or "@" not in cleaned_from or any(ch.isspace() for ch in cleaned_from):
            raise ValueError("--from must be a valid email address.")
        args.from_email = cleaned_from
    if not args.reply_to_id:
        if not (args.subject or "").strip():
            raise ValueError("--subject is required when creating a new thread.")
        removed_lower = {addr.lower() for _, addr in _split_emails(args.remove)}
        if not _dedupe_recipients(_split_emails(args.to), removed_lower):
            raise ValueError("--to is required when creating a new thread.")
    for attachment_path in args.attach:
        if not attachment_path.is_file():
            raise ValueError(f"Attachment not found: {attachment_path}")
    return body_html


def _upload_and_readback(
    gws_dir: Path,
    raw_message: dict[str, Any],
    draft_id_arg: str | None,
) -> tuple[str, dict[str, Any]]:
    """Stage message.eml in gws_dir, upload via drafts.create/update, and read back the saved draft."""
    # Upload the RFC 5322 bytes as media: one argument over Linux's 128 KiB limit fails with E2BIG.
    message = dict(raw_message)
    raw = message.pop("raw")
    operation = "update" if draft_id_arg else "create"
    params: dict[str, Any] = {"userId": "me"}
    metadata: dict[str, Any] = {"message": message} if message else {}
    if draft_id_arg:
        params["id"] = metadata["id"] = draft_id_arg
    eml_path = gws_dir / "message.eml"
    eml_path.write_bytes(decode_b64url_bytes(raw))
    resp = _run_gws(
        [
            "gmail",
            "users",
            "drafts",
            operation,
            "--params",
            json.dumps(params),
            "--json",
            json.dumps(metadata),
            "--upload",
            eml_path.name,
            "--upload-content-type",
            "message/rfc822",
            "--format",
            "json",
        ],
        f"drafts.{operation}",
        cwd=gws_dir,
    )

    draft_id = str(resp.get("id") or "").strip()
    if not draft_id:
        raise RuntimeError(
            f"drafts.{operation} returned no draft id; do not create the draft again: find it with "
            "`gws gmail users drafts list` and rerun with --draft-id <id>."
        )
    try:
        readback = _run_gws(
            [
                "gmail",
                "users",
                "drafts",
                "get",
                "--params",
                json.dumps({"userId": "me", "id": draft_id, "format": "full"}),
                "--format",
                "json",
            ],
            "drafts.get",
            cwd=gws_dir,
        )
    except RuntimeError as error:
        # The draft exists: name it so a retry updates it instead of creating a duplicate.
        raise RuntimeError(
            f"draft {draft_id} was saved, but its read-back failed ({error}); do not create it again: "
            f"rerun with --draft-id {draft_id} to update and verify it in place."
        ) from error
    return draft_id, readback


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for validating, composing, and creating or updating a Gmail draft."""
    args = _build_parser().parse_args(argv)

    try:
        body_html = _validate_inputs(args)
        prose_errors, prose_warnings = check_prose_with_vale(
            body_html,
            ext=".html",
            label="stdin" if args.input == "-" else Path(args.input).name,
            cwd=None if args.input == "-" else Path(args.input).resolve().parent,
        )
        if prose_errors:
            raise ValueError("Prose lint failed: " + "; ".join(prose_errors))
        for warning in prose_warnings:
            sys.stderr.write(f"draft_email warning: {warning}\n")
        # gws loads a `.env` from its working directory upward and rejects --upload paths outside that
        # directory, so every gws call of this run uses one private temporary directory: the reads, the
        # upload, and the read-back resolve the same account, and the message stays out of the caller's checkout.
        with tempfile.TemporaryDirectory(prefix="draft-mail-") as tmp:
            gws_dir = Path(tmp)
            send_as = resolve_send_as(args.from_email, cwd=gws_dir)

            parent_msg: dict[str, Any] | None = None
            if args.reply_to_id:
                params = json.dumps({"userId": "me", "id": args.reply_to_id, "format": "full"})
                parent_msg = _run_gws(
                    ["gmail", "users", "messages", "get", "--params", params, "--format", "json"],
                    "messages.get",
                    cwd=gws_dir,
                )

            built = compose_draft_payload(
                body_html,
                send_as=send_as,
                to_flags=args.to,
                cc_flags=args.cc,
                bcc_flags=args.bcc,
                remove_flags=args.remove,
                subject=args.subject,
                parent_msg=parent_msg,
                reply_all=args.reply_all,
                attachments=args.attach,
            )

            if args.dry_run:
                out = {
                    "dry_run": True,
                    "operation": "users.drafts.update" if args.draft_id else "users.drafts.create",
                    "draftId": args.draft_id,
                    **built["summary"],
                    "rawLength": len(built["draft"]["message"]["raw"]),
                }
                if prose_warnings:
                    out["proseWarnings"] = prose_warnings
                sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
                return 0

            draft_id, readback = _upload_and_readback(gws_dir, built["draft"]["message"], args.draft_id)
        msg_obj = readback.get("message") or {}
        payload_obj = msg_obj.get("payload") or {}
        out = {
            **built["summary"],
            "draftId": draft_id,
            "messageId": msg_obj.get("id"),
            "threadId": msg_obj.get("threadId") or built["summary"]["threadId"],
            "mimeType": payload_obj.get("mimeType"),
            "partMimeTypes": [p.get("mimeType") for p in (payload_obj.get("parts") or []) if isinstance(p, dict)],
        }
        if prose_warnings:
            out["proseWarnings"] = prose_warnings
        sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
        return 0
    except UnicodeDecodeError:
        sys.stderr.write("draft_email: Input body is not valid UTF-8.\n")
        return 1
    except (OSError, ValueError, RuntimeError) as error:
        sys.stderr.write(f"draft_email: {error}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
