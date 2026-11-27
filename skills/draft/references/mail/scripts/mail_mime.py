"""HTML validation, plain-text conversion, MIME parsing, recipient formatting, and reply context helpers."""

from __future__ import annotations

import base64
import html
import json
import mimetypes
import os
import re
import shutil
import stat
import subprocess
import sys
from email.message import EmailMessage
from email.policy import SMTP
from email.utils import getaddresses, parseaddr
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

HTML_TAG_RE = re.compile(
    r"<\s*(?:p|div|br|hr|mark|ul|ol|li|table|thead|tbody|tr|td|th|blockquote|strong|b|em|i|u|a|code|pre|span|h[1-6])\b",
    re.IGNORECASE,
)
CODE_BLOCK_RE = re.compile(r"<(pre|code)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
BODY_INNER_RE = re.compile(r"<body\b[^>]*>(.*)</body>", re.IGNORECASE | re.DOTALL)
DIV_TOKEN_RE = re.compile(r"<(/?)div\b[^>]*>", re.IGNORECASE)
OPEN_DIR_LTR_RE = re.compile(r"\A<div\s+dir=[\"']ltr[\"']\s*>", re.IGNORECASE)


def _unwrap_outer_dir_ltr(fragment: str) -> str:
    """Strip a single balanced outer <div dir="ltr">...</div> wrapper if present."""
    stripped = fragment.strip()
    open_match = OPEN_DIR_LTR_RE.match(stripped)
    if not open_match or not stripped.lower().endswith("</div>"):
        return stripped
    depth = 0
    tokens = list(DIV_TOKEN_RE.finditer(stripped))
    for idx, token in enumerate(tokens):
        depth += -1 if token.group(1) == "/" else 1
        if depth == 0 and idx < len(tokens) - 1:
            return stripped
    if depth == 0 and tokens:
        return stripped[open_match.end() : tokens[-1].start()].strip()
    return stripped


class _HTMLToTextParser(HTMLParser):
    """Convert an HTML email fragment into a readable plain-text fallback."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.chunks: list[str] = []
        self._href_stack: list[tuple[str | None, int]] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style"}:
            self._skip_depth += 1
            return
        if self._skip_depth > 0:
            return
        if tag == "br":
            self.chunks.append("\n")
        elif tag == "hr":
            self.chunks.append("\n---\n\n")
        elif tag == "li":
            self.chunks.append("\n- ")
        elif tag in {"p", "div", "tr", "blockquote", "pre", "h1", "h2", "h3", "h4", "h5", "h6"}:
            if self.chunks and not self.chunks[-1].endswith("\n"):
                self.chunks.append("\n")
        elif tag == "a":
            href = dict(attrs).get("href")
            self._href_stack.append((href, len(self.chunks)))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style"}:
            if self._skip_depth > 0:
                self._skip_depth -= 1
            return
        if self._skip_depth > 0:
            return
        if tag in {"p", "blockquote", "pre", "ul", "ol", "table", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.chunks.append("\n\n")
        elif tag in {"div", "tr", "li"}:
            self.chunks.append("\n")
        elif tag in {"td", "th"}:
            self.chunks.append("\t")
        elif tag == "a" and self._href_stack:
            href, start_idx = self._href_stack.pop()
            anchor_text = "".join(self.chunks[start_idx:]).strip()
            if href and href.startswith(("http://", "https://")) and href not in anchor_text:
                self.chunks.append(f" ({href})")

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        self.chunks.append(data)

    def get_text(self) -> str:
        raw = "".join(self.chunks)
        lines = [line.rstrip() for line in raw.splitlines()]
        collapsed = "\n".join(lines)
        collapsed = re.sub(r"\n{3,}", "\n\n", collapsed)
        return collapsed.strip()


_SAFE_QUOTE_TAGS = frozenset(
    {
        "a",
        "b",
        "blockquote",
        "br",
        "code",
        "div",
        "em",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
        "i",
        "li",
        "mark",
        "ol",
        "p",
        "pre",
        "span",
        "strong",
        "table",
        "tbody",
        "td",
        "th",
        "thead",
        "tr",
        "u",
        "ul",
    }
)
_VOID_QUOTE_TAGS = frozenset({"br", "hr"})
_DROP_CONTENT_TAGS = frozenset({"script", "style", "iframe", "object", "embed", "noscript", "template"})
_SAFE_DIR_VALUES = frozenset({"ltr", "rtl", "auto"})


class _QuotedHTMLSanitizer(HTMLParser):
    """Allowlist HTML sanitizer that strips active markup and balances tags for quoted replies."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._out: list[str] = []
        self._open_tags: list[str] = []
        self._drop_depth = 0

    def _safe_attrs(self, tag: str, attrs: list[tuple[str, str | None]]) -> str:
        kept: list[str] = []
        for raw_name, raw_val in attrs:
            name = raw_name.lower()
            if raw_val is None:
                continue
            val = raw_val.strip()
            if name == "dir" and val.lower() in _SAFE_DIR_VALUES:
                kept.append(f' dir="{val.lower()}"')
            elif (
                tag == "a"
                and name == "href"
                and val.lower().startswith(("http://", "https://", "mailto:"))
                and not any(ord(ch) < 32 or ord(ch) == 127 for ch in val)
            ):
                kept.append(f' href="{html.escape(val, quote=True)}"')
            elif tag in {"td", "th"} and name in {"colspan", "rowspan"} and val.isdigit():
                kept.append(f' {name}="{val}"')
        return "".join(kept)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in _DROP_CONTENT_TAGS:
            self._drop_depth += 1
            return
        if self._drop_depth > 0 or tag not in _SAFE_QUOTE_TAGS:
            return
        attr_str = self._safe_attrs(tag, attrs)
        self._out.append(f"<{tag}{attr_str}>")
        if tag not in _VOID_QUOTE_TAGS:
            self._open_tags.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self._drop_depth > 0 or tag not in _SAFE_QUOTE_TAGS:
            return
        attr_str = self._safe_attrs(tag, attrs)
        self._out.append(f"<{tag}{attr_str}>")
        if tag not in _VOID_QUOTE_TAGS:
            self._out.append(f"</{tag}>")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _DROP_CONTENT_TAGS:
            if self._drop_depth > 0:
                self._drop_depth -= 1
            return
        if self._drop_depth > 0 or tag not in self._open_tags:
            return
        while self._open_tags:
            popped = self._open_tags.pop()
            self._out.append(f"</{popped}>")
            if popped == tag:
                break

    def handle_data(self, data: str) -> None:
        if self._drop_depth > 0:
            return
        self._out.append(html.escape(data, quote=False))

    def finish(self) -> str:
        while self._open_tags:
            self._out.append(f"</{self._open_tags.pop()}>")
        return "".join(self._out)


def _sanitize_quoted_html(fragment: str) -> str:
    """Strip active content and balance tags in untrusted parent HTML before embedding in replies."""
    sanitizer = _QuotedHTMLSanitizer()
    sanitizer.feed(fragment)
    sanitizer.close()
    return sanitizer.finish()


def html_to_text(fragment: str) -> str:
    """Return a clean plain-text rendering of an HTML fragment."""
    parser = _HTMLToTextParser()
    parser.feed(fragment)
    parser.close()
    return parser.get_text()


def validate_html_fragment(fragment: str) -> str:
    """Validate that the authored email body is rich HTML without raw Markdown syntax."""
    cleaned = fragment.strip()
    if not cleaned:
        raise ValueError("Email HTML body is empty; supply a non-empty UTF-8 HTML fragment.")
    body_match = BODY_INNER_RE.search(cleaned)
    if body_match:
        cleaned = body_match.group(1).strip()
    if re.search(r"<\s*(?:script|style)\b", cleaned, re.IGNORECASE):
        raise ValueError("Unsupported <script> or <style> tag found in HTML body; use inline styles only.")
    if not HTML_TAG_RE.search(cleaned):
        raise ValueError(
            'Plain-text body rejected: write an HTML fragment (<p>, <ul><li>, <strong>, <a href="...">) '
            "so the draft is rich HTML."
        )
    prose = CODE_BLOCK_RE.sub("", cleaned)
    text_only = re.sub(r"<[^>]+>", "\n", prose)
    if re.search(r"(?m)^\s{0,3}#{1,6}\s+\S", text_only):
        raise ValueError("Raw Markdown heading found in HTML body; use <p><strong>...</strong></p> instead.")
    if re.search(r"\*\*[^*\n]+\*\*", text_only):
        raise ValueError("Raw Markdown **bold** found in HTML body; use <strong>...</strong> instead.")
    if re.search(r"\[[^\]\n]+\]\(https?://[^)\s]+\)", text_only):
        raise ValueError('Raw Markdown [text](url) link found in HTML body; use <a href="...">...</a> instead.')
    if re.search(r"(?m)^\s*`{3,}", text_only):
        raise ValueError("Raw Markdown code fence (```) found in HTML body; use <pre><code>...</code></pre> instead.")
    if re.search(r"`[^`\n]+`", text_only):
        raise ValueError(
            "Raw Markdown `inline code` found in HTML body; write plain prose or use <code>...</code> strictly for copyable commands."
        )
    if re.search(
        r"(?m)^\s*\|?[^\n|]+\|[^\n]*\n\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$",
        text_only,
    ):
        raise ValueError("Raw Markdown table found in HTML body; use <table><tr><th>...</th></tr>...</table> instead.")
    return cleaned


def decode_b64url_bytes(data: str) -> bytes:
    """Decode unpadded or padded base64url ASCII text into raw bytes."""
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _decode_b64url(data: str) -> str:
    """Decode base64url UTF-8 text with replacement for malformed sequences."""
    return decode_b64url_bytes(data).decode("utf-8", errors="replace")


def _headers_map(payload: dict[str, Any]) -> dict[str, str]:
    """Return a first-seen lowercase header map from a Gmail MIME payload."""
    headers: dict[str, str] = {}
    for item in payload.get("headers") or []:
        if isinstance(item, dict):
            name = str(item.get("name") or "").strip()
            value = str(item.get("value") or "").strip()
            if name and name.lower() not in headers:
                headers[name.lower()] = value
    return headers


def _find_mime_part(part: dict[str, Any], target_mime: str) -> str | None:
    """Recursively extract the first decoded inline body matching target_mime, skipping attachments."""
    if part.get("filename"):
        return None
    disposition = _headers_map(part).get("content-disposition") or ""
    if disposition.lower().startswith("attachment"):
        return None
    mime_type = str(part.get("mimeType") or "").lower()
    body_data = (part.get("body") or {}).get("data")
    if mime_type == target_mime and isinstance(body_data, str) and body_data:
        return _decode_b64url(body_data)
    for child in part.get("parts") or []:
        if isinstance(child, dict):
            found = _find_mime_part(child, target_mime)
            if found is not None:
                return found
    return None


def _split_emails(raw_values: list[str]) -> list[tuple[str, str]]:
    """Return (display_name, email) pairs from comma-separated header/flag strings."""
    return [(name.strip(), addr.strip()) for name, addr in getaddresses(raw_values) if addr.strip()]


def _format_recipient(name: str, addr: str) -> str:
    """Format a display name and address as readable UTF-8 for EmailMessage headers."""
    clean_name = " ".join(name.split())
    if not clean_name:
        return addr
    if any(ch in clean_name for ch in ',;<>@"():\\.[]'):
        escaped = clean_name.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}" <{addr}>'
    return f"{clean_name} <{addr}>"


def _dedupe_recipients(
    candidates: list[tuple[str, str]],
    exclude_lower: set[str],
) -> list[str]:
    """Format and deduplicate recipients by lowercase email address."""
    seen: set[str] = set()
    formatted: list[str] = []
    for name, addr in candidates:
        key = addr.lower()
        if key in exclude_lower or key in seen:
            continue
        seen.add(key)
        formatted.append(_format_recipient(name, addr))
    return formatted


def _format_gmail_attr(date_str: str, from_raw: str) -> str:
    """Build the HTML attribution line inside <div dir="ltr" class="gmail_attr">."""
    name, addr = parseaddr(from_raw)
    if name and addr:
        sender_html = (
            f'{html.escape(name)} &lt;<a href="mailto:{html.escape(addr, quote=True)}">{html.escape(addr)}</a>&gt;'
        )
    elif addr:
        sender_html = f'<a href="mailto:{html.escape(addr, quote=True)}">{html.escape(addr)}</a>'
    else:
        sender_html = html.escape(from_raw or "sender")
    when = f"On {html.escape(date_str)}, " if date_str else ""
    return f"{when}{sender_html} wrote:<br>"


def extract_reply_context(parent_msg: dict[str, Any]) -> dict[str, str]:
    """Extract thread continuity headers and quoted HTML/plain bodies from a parent Gmail message."""
    thread_id = str(parent_msg.get("threadId") or "").strip()
    if not thread_id:
        raise ValueError("Parent message is missing threadId.")
    payload = parent_msg.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("Parent message is missing payload; fetch with format=full.")

    headers = _headers_map(payload)
    message_id = headers.get("message-id") or ""
    if not message_id:
        raise ValueError("Parent message is missing a Message-ID header.")
    existing_refs = headers.get("references") or ""
    references = existing_refs if message_id in existing_refs.split() else f"{existing_refs} {message_id}".strip()

    raw_subject = headers.get("subject") or ""
    subject = raw_subject if raw_subject.lower().startswith("re:") else f"Re: {raw_subject}".strip()

    parent_html = _find_mime_part(payload, "text/html")
    parent_text = _find_mime_part(payload, "text/plain")
    if parent_html is not None:
        inner = BODY_INNER_RE.search(parent_html)
        parent_html = inner.group(1).strip() if inner else parent_html.strip()
        if parent_text is None:
            parent_text = html_to_text(parent_html)
        parent_html = _sanitize_quoted_html(parent_html)
    elif parent_text is not None:
        parent_text = parent_text.strip()
        normalized = parent_text.replace("\r\n", "\n").replace("\r", "\n")
        parent_html = f'<div dir="ltr">{html.escape(normalized).replace(chr(10), "<br>")}</div>'
    else:
        snippet = str(parent_msg.get("snippet") or "").strip()
        parent_text = snippet
        parent_html = f'<div dir="ltr">{html.escape(snippet)}</div>'

    return {
        "threadId": thread_id,
        "messageId": message_id,
        "references": references,
        "subject": subject,
        "from": headers.get("from") or "",
        "replyTo": headers.get("reply-to") or headers.get("from") or "",
        "to": headers.get("to") or "",
        "cc": headers.get("cc") or "",
        "date": headers.get("date") or "",
        "quotedHtml": parent_html,
        "quotedText": parent_text,
    }


def build_signature_blocks(signature_html: str) -> tuple[str, str]:
    """Render Gmail HTML and plain-text signature blocks from a sendAs signature fragment."""
    if not signature_html:
        return "", ""
    sig_block_html = (
        '<br clear="all"><div><br></div>'
        f'<div dir="ltr" class="gmail_signature" data-smartmail="gmail_signature">{signature_html}</div>'
    )
    sig_text = html_to_text(signature_html)
    sig_block_text = f"\n\n-- \n{sig_text}" if sig_text else ""
    return sig_block_html, sig_block_text


def build_quote_blocks(reply_ctx: dict[str, str]) -> tuple[str, str]:
    """Render Gmail collapsible HTML and plain-text quote blocks from reply context."""
    attr_html = _format_gmail_attr(reply_ctx["date"], reply_ctx["from"])
    safe_quoted_html = _sanitize_quoted_html(reply_ctx["quotedHtml"])
    quote_block_html = (
        '<br><div class="gmail_quote gmail_quote_container">'
        f'<div dir="ltr" class="gmail_attr">{attr_html}</div>'
        '<blockquote class="gmail_quote" '
        'style="margin:0px 0px 0px 0.8ex;border-left:1px solid rgb(204,204,204);padding-left:1ex">'
        f"{safe_quoted_html}"
        "</blockquote></div>"
    )
    when_prefix = f"On {reply_ctx['date']}, " if reply_ctx["date"] else ""
    quoted_lines = "\n".join(f"> {line}" if line else ">" for line in reply_ctx["quotedText"].splitlines())
    quote_block_text = f"\n\n{when_prefix}{reply_ctx['from']} wrote:\n{quoted_lines}"
    return quote_block_html, quote_block_text


def build_raw_mime_message(
    *,
    from_header: str,
    to_recipients: list[str],
    cc_recipients: list[str],
    bcc_recipients: list[str],
    subject: str,
    full_text: str,
    full_html: str,
    in_reply_to: str | None = None,
    references: str | None = None,
    attachments: list[Path] | None = None,
) -> tuple[str, str]:
    """Assemble an RFC 5322 multipart/alternative message and return (raw_b64url, content_type)."""
    msg = EmailMessage(policy=SMTP)
    msg["From"] = from_header
    msg["To"] = ", ".join(to_recipients)
    if cc_recipients:
        msg["Cc"] = ", ".join(cc_recipients)
    if bcc_recipients:
        msg["Bcc"] = ", ".join(bcc_recipients)
    msg["Subject"] = subject
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = references

    msg.set_content(full_text, subtype="plain", charset="utf-8")
    msg.add_alternative(full_html, subtype="html", charset="utf-8")

    for attachment_path in attachments or []:
        data = attachment_path.read_bytes()
        guessed_type, _ = mimetypes.guess_type(attachment_path.name)
        maintype, subtype = (guessed_type or "application/octet-stream").split("/", 1)
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=attachment_path.name)

    raw_b64 = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii").rstrip("=")
    return raw_b64, msg.get_content_type()


def _resolve_reply_recipients(
    reply_ctx: dict[str, str],
    *,
    to_flags: list[str],
    cc_flags: list[str],
    exclude_self_and_removed: set[str],
    removed_lower: set[str],
    reply_all: bool,
) -> tuple[list[str], list[str]]:
    """Resolve deduplicated To and Cc headers for a reply draft."""
    reply_target_pairs = _split_emails([reply_ctx["replyTo"]])
    extra_to_pairs = _split_emails(to_flags)
    to_recipients = _dedupe_recipients(reply_target_pairs + extra_to_pairs, exclude_self_and_removed)
    if not to_recipients:
        # Replying to a message sent by self: address the original To recipients first
        to_recipients = _dedupe_recipients(
            _split_emails([reply_ctx["to"]]) + extra_to_pairs,
            exclude_self_and_removed,
        )
    if not to_recipients:
        # Note-to-self fallback: keep the original reply target unless explicitly removed
        to_recipients = _dedupe_recipients(
            reply_target_pairs + _split_emails([reply_ctx["to"]]) + extra_to_pairs,
            removed_lower,
        )
    if not to_recipients:
        raise ValueError("No To recipient remains after exclusions; pass --to.")

    to_lower = {addr.lower() for _, addr in _split_emails(to_recipients)}
    cc_candidates: list[tuple[str, str]] = []
    if reply_all:
        cc_candidates.extend(_split_emails([reply_ctx["to"], reply_ctx["cc"]]))
    cc_candidates.extend(_split_emails(cc_flags))
    cc_recipients = _dedupe_recipients(cc_candidates, exclude_self_and_removed | to_lower)
    return to_recipients, cc_recipients


def resolve_recipients(
    *,
    send_as_email: str,
    to_flags: list[str],
    cc_flags: list[str],
    bcc_flags: list[str],
    remove_flags: list[str],
    reply_ctx: dict[str, str] | None = None,
    reply_all: bool = False,
) -> tuple[list[str], list[str], list[str]]:
    """Resolve deduplicated To, Cc, and Bcc recipient lists for a reply or new thread."""
    removed_lower = {addr.lower() for _, addr in _split_emails(remove_flags)}
    if reply_ctx is not None:
        exclude_self_and_removed = {send_as_email.lower(), *removed_lower}
        to_recipients, cc_recipients = _resolve_reply_recipients(
            reply_ctx,
            to_flags=to_flags,
            cc_flags=cc_flags,
            exclude_self_and_removed=exclude_self_and_removed,
            removed_lower=removed_lower,
            reply_all=reply_all,
        )
    else:
        to_recipients = _dedupe_recipients(_split_emails(to_flags), removed_lower)
        if not to_recipients:
            raise ValueError("--to is required when creating a new thread.")
        to_lower = {addr.lower() for _, addr in _split_emails(to_recipients)}
        cc_recipients = _dedupe_recipients(_split_emails(cc_flags), removed_lower | to_lower)

    bcc_recipients = _dedupe_recipients(
        _split_emails(bcc_flags),
        removed_lower | {addr.lower() for _, addr in _split_emails(to_recipients + cc_recipients)},
    )
    return to_recipients, cc_recipients, bcc_recipients


def _is_trusted_vale_config(path: Path) -> bool:
    try:
        uid = os.getuid()
        st = path.lstat()
        if not (stat.S_ISREG(st.st_mode) and st.st_uid in (0, uid) and stat.S_IMODE(st.st_mode) & 0o022 == 0):
            return False
        for idx, directory in enumerate((path.parent, *path.parent.parents)):
            dst = directory.lstat()
            if not stat.S_ISDIR(dst.st_mode) or dst.st_uid not in (0, uid):
                return False
            # Allow sticky root-owned temp roots (e.g. /tmp) above the immediate parent only.
            if stat.S_IMODE(dst.st_mode) & 0o022 != 0 and (
                idx == 0 or dst.st_uid != 0 or not (dst.st_mode & stat.S_ISVTX)
            ):
                return False
    except OSError:
        return False
    return True


def _resolve_vale_config(cwd: Path | None = None) -> Path | None:
    """Return the nearest trusted project .vale.ini or the global ~/.config/vale/.vale.ini if present."""
    start = (cwd or Path.cwd()).resolve()
    for parent in (start, *start.parents):
        candidate = parent / ".vale.ini"
        if _is_trusted_vale_config(candidate):
            return candidate
    global_cfg = Path.home() / ".config/vale/.vale.ini"
    return global_cfg if _is_trusted_vale_config(global_cfg) else None


def check_prose_with_vale(
    text: str,
    *,
    ext: str = ".html",
    label: str = "body.html",
    cwd: Path | None = None,
) -> tuple[list[str], list[str]]:
    """Run Vale prose checks on text when Vale and a config file are available, returning (errors, warnings)."""
    vale_bin = shutil.which("vale")
    if not vale_bin:
        sys.stderr.write("draft_email warning: vale not found on PATH; skipping prose lint.\n")
        return [], []
    config = _resolve_vale_config(cwd)
    if config is None:
        sys.stderr.write("draft_email warning: no trusted .vale.ini found; skipping prose lint.\n")
        return [], []
    try:
        proc = subprocess.run(  # noqa: S603 - fixed Vale binary and resolved config path
            [vale_bin, "--no-global", "--config", str(config), "--output=JSON", f"--ext={ext}"],
            input=text,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"vale timed out on {label}") from exc
    if proc.returncode not in {0, 1}:
        detail = (proc.stderr or proc.stdout).strip()
        raise RuntimeError(f"vale failed on {label}: {detail}")
    raw = proc.stdout.strip()
    if not raw:
        if proc.returncode == 1:
            detail = proc.stderr.strip() or "exit status 1 with empty JSON output"
            raise RuntimeError(f"vale failed on {label}: {detail}")
        return [], []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"vale returned invalid JSON on {label}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"vale returned non-object JSON on {label}")
    errors: list[str] = []
    warnings: list[str] = []
    for findings in data.values():
        for item in findings:
            line = item.get("Line", 1)
            check = item.get("Check", "Vale")
            message = item.get("Message", "")
            match = str(item.get("Match") or "").strip()
            suffix = f" ({match})" if match and match not in message and len(match) <= 40 else ""
            formatted = f"{label}:{line}: [{check}] {message}{suffix}"
            if item.get("Severity") == "error":
                errors.append(formatted)
            else:
                warnings.append(formatted)
    if proc.returncode == 1 and not errors:
        detail = (proc.stderr or raw).strip()[:200]
        raise RuntimeError(f"vale failed on {label} without error findings: {detail}")
    return errors, warnings
