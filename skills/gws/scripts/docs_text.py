#!/usr/bin/env python3
"""Extract labeled text sections from saved Docs JSON, including nested tabs."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any


class InputError(ValueError):
    """A recovery message that is safe to print: fixed text or a character offset, never document content."""


def chip(kind: str, label: str | None) -> str:
    """Label a smart chip like the inline-object placeholder, keeping its displayed text."""
    return f"[{kind}: {label}]" if label else f"[{kind}]"


def structural_text(elements: list[dict[str, Any]]) -> str:
    """Walk document structure without collecting suggested/repeated metadata text."""
    result: list[str] = []
    for element in elements:
        if "paragraph" in element:
            for run in (element["paragraph"] or {}).get("elements") or []:
                if "textRun" in run:
                    result.append(run["textRun"]["content"])
                elif "inlineObjectElement" in run:
                    result.append("[inline object]")
                elif "person" in run:
                    # The chip shows the name when present, otherwise the email.
                    person = (run["person"] or {}).get("personProperties") or {}
                    result.append(chip("person", person.get("name") or person.get("email")))
                elif "richLink" in run:
                    link = (run["richLink"] or {}).get("richLinkProperties") or {}
                    result.append(chip("link", link.get("title") or link.get("uri")))
                elif "dateElement" in run:
                    date = (run["dateElement"] or {}).get("dateElementProperties") or {}
                    result.append(chip("date", date.get("displayText")))
                elif "dropdown" in run:
                    dropdown = (run["dropdown"] or {}).get("dropdownProperties") or {}
                    result.append(chip("dropdown", dropdown.get("displayValue")))
        elif "table" in element:
            for row in (element["table"] or {}).get("tableRows") or []:
                cells = [
                    structural_text(cell.get("content") or []).rstrip("\n") for cell in (row.get("tableCells") or [])
                ]
                result.append("\t".join(cells) + "\n")
        elif "tableOfContents" in element:
            result.append(structural_text((element["tableOfContents"] or {}).get("content") or []))
    return "".join(result)


def extract(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict) or "error" in document:
        raise InputError("Expected a successful documents.get object.")
    sections: list[dict[str, Any]] = []

    def add_sections(content: dict[str, Any], tab_id: str | None, title: str | None) -> None:
        if "body" not in content or not isinstance(content["body"], dict):
            raise InputError("Body missing; fetch document content without a metadata-only field mask.")
        groups: list[tuple[str, str, dict[str, Any]]] = [("body", "body", content["body"])]
        for kind in ("headers", "footers", "footnotes"):
            groups.extend((kind, key, value) for key, value in (content.get(kind) or {}).items())
        for kind, section_id, section in groups:
            sections.append(
                {
                    "tabId": tab_id,
                    "tabTitle": title,
                    "kind": kind,
                    "id": section_id,
                    "text": structural_text((section or {}).get("content") or []),
                }
            )

    def visit(tabs: list[dict[str, Any]]) -> None:
        for tab in tabs:
            properties = tab["tabProperties"]
            add_sections(tab["documentTab"], properties["tabId"], properties.get("title"))
            visit(tab.get("childTabs") or [])

    if document.get("tabs"):
        visit(document["tabs"])
    elif "body" in document:
        add_sections(document, None, None)
    else:
        raise InputError("No body or tabs; fetch documents.get with includeTabsContent=true.")
    return {
        "documentId": document.get("documentId"),
        "title": document.get("title"),
        "coverage": "text-only; legacy body covers only the first tab"
        if not document.get("tabs")
        else "text-only; returned tabs",
        "sections": sections,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Saved documents.get JSON file, or - for stdin")
    args = parser.parse_args()
    try:
        text = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
        try:
            document = json.loads(text)
        except json.JSONDecodeError as error:
            raise InputError(f"Invalid JSON near character {error.pos}.") from error
        result = extract(document)
    except InputError as error:
        sys.stderr.write(f"docs_text: {error}\n")
        return 1
    # Other errors can quote the input (a UnicodeDecodeError names its bytes), so print only their type.
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        sys.stderr.write(
            f"docs_text: Invalid or unreadable Docs input ({type(error).__name__}); fetch full tab content.\n"
        )
        return 1
    sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
