#!/usr/bin/env python3
"""Prepare a Google Chat text request from a UTF-8 file; never send it."""

import argparse
import json
import re
import sys
from pathlib import Path


def build_body(text: str, syntax: str, thread: str | None = None) -> dict:
    """Preserve authored content and reject common unsupported message layouts."""
    if not text.strip():
        raise ValueError("Message is empty; supply a non-empty UTF-8 text file.")
    # Leave room for JSON and thread metadata below Chat's 32 KB message limit.
    if len(text.encode("utf-8")) > 30000:
        raise ValueError("Text exceeds the helper's 30000-byte budget; shorten it or link a document.")
    fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            if not fence and line.strip() != "```":
                raise ValueError("Use bare triple-backtick fences without a language label in Chat.")
            fence = not fence
            continue
        if fence:
            continue
        # Inline code is literal too; examples such as `**kwargs` are not bold.
        prose = re.sub(r"(`+).*?\1", "", line)
        if re.match(r"^\s{0,3}#{1,6}\s", prose):
            raise ValueError("Replace Markdown headings with a short bold label in the selected syntax.")
        if re.match(r"^\s*\|?\s*:?-{3,}:?\s*\|", prose):
            raise ValueError("Replace the Markdown table with labeled bullets or link a Sheet.")
        if syntax == "chat" and re.search(r"\*\*\S|\[[^\]]+\]\(", prose):
            raise ValueError("Markdown bold/link found: use --syntax markdown or author native Chat markup.")
    if fence:
        raise ValueError("Close the triple-backtick code block before preparing the message.")
    body = {"text": text}
    if syntax == "markdown":
        body["markupSyntax"] = "MARKUP_SYNTAX_MARKDOWN"
    if thread:
        if not re.fullmatch(r"spaces/[^/\s]+/threads/[^/\s]+", thread):
            raise ValueError("Thread must be an observed spaces/SPACE/threads/THREAD resource name.")
        body["thread"] = {"name": thread}
    return body


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="UTF-8 text file, or - for stdin")
    parser.add_argument("--syntax", choices=("chat", "markdown"), default="chat")
    parser.add_argument("--thread", help="Existing thread resource; also set messageReplyOption in --params")
    args = parser.parse_args()
    try:
        text = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
        body = build_body(text, args.syntax, args.thread)
    except (OSError, ValueError) as error:
        sys.stderr.write(f"chat_body: {error}\n")
        return 1
    sys.stdout.write(json.dumps(body, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
