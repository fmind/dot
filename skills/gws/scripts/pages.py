#!/usr/bin/env python3
"""Combine saved gws JSON/NDJSON pages, retaining pagination completeness."""

import argparse
import json
import sys
from pathlib import Path


def collect(text: str, field: str, allow_incomplete: bool = False) -> dict:
    """Decode JSON values, not Unicode-aware lines (content can contain U+2028)."""
    decoder = json.JSONDecoder()
    pages = []
    offset = 0
    while offset < len(text):
        if text[offset] in " \t\r\n":
            offset += 1
            continue
        try:
            page, offset = decoder.raw_decode(text, offset)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON near character {error.pos}; retain only gws stdout.") from error
        if not isinstance(page, dict) or "error" in page:
            raise ValueError("Expected successful page objects; check the original gws exit status/error.")
        items = page.get(field, [])  # Google omits empty repeated fields.
        if not isinstance(items, list):
            raise TypeError("The requested top-level items field must contain an array.")
        if not isinstance(page.get("nextPageToken", ""), str):
            raise TypeError("nextPageToken must be a string.")
        if not isinstance(page.get("incompleteSearch", False), bool):
            raise TypeError("incompleteSearch must be a boolean.")
        if pages and not pages[-1].get("nextPageToken"):
            raise ValueError("Page after a terminal page; do not concatenate separate queries.")
        pages.append(page)
    if not pages:
        raise ValueError("No pages found; an empty stream is not a successful empty result.")
    token = pages[-1].get("nextPageToken") or None
    incomplete_search = any(page.get("incompleteSearch", False) for page in pages)
    complete = not token and not incomplete_search
    if not complete and not allow_incomplete:
        raise ValueError(
            "Results are incomplete; narrow/refine the query or use --allow-incomplete for a labeled sample."
        )
    return {
        "items": [item for page in pages for item in page.get(field, [])],
        "pageCount": len(pages),
        "complete": complete,
        "nextPageToken": token,
        "incompleteSearch": incomplete_search,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Saved JSON/NDJSON file, or - for stdin")
    parser.add_argument("--items", required=True, help="Top-level array key, e.g. files, messages, spaces, items")
    parser.add_argument("--allow-incomplete", action="store_true", help="Emit partial data with complete=false")
    args = parser.parse_args()
    try:
        text = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
        result = collect(text, args.items, args.allow_incomplete)
    except (OSError, ValueError, TypeError) as error:
        sys.stderr.write(f"pages: {error}\n")
        return 1
    sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
