#!/usr/bin/env python3
"""Extract labeled text sections from saved Docs JSON, including nested tabs."""

import argparse
import json
import sys
from pathlib import Path


def structural_text(elements: list) -> str:
    """Walk document structure without collecting suggested/repeated metadata text."""
    result = []
    for element in elements:
        if "paragraph" in element:
            for run in element["paragraph"].get("elements", []):
                if "textRun" in run:
                    result.append(run["textRun"]["content"])
                elif "inlineObjectElement" in run:
                    result.append("[inline object]")
        elif "table" in element:
            for row in element["table"].get("tableRows", []):
                cells = [structural_text(cell.get("content", [])).rstrip("\n") for cell in row.get("tableCells", [])]
                result.append("\t".join(cells) + "\n")
        elif "tableOfContents" in element:
            result.append(structural_text(element["tableOfContents"].get("content", [])))
    return "".join(result)


def extract(document: dict) -> dict:
    if not isinstance(document, dict) or "error" in document:
        raise ValueError("Expected a successful documents.get object.")
    sections = []

    def add_sections(content: dict, tab_id: str | None, title: str | None) -> None:
        if "body" not in content:
            raise ValueError("Body missing; fetch document content without a metadata-only field mask.")
        groups = [("body", "body", content["body"])]
        for kind in ("headers", "footers", "footnotes"):
            groups.extend((kind, key, value) for key, value in content.get(kind, {}).items())
        for kind, section_id, section in groups:
            sections.append(
                {
                    "tabId": tab_id,
                    "tabTitle": title,
                    "kind": kind,
                    "id": section_id,
                    "text": structural_text(section.get("content", [])),
                }
            )

    def visit(tabs: list) -> None:
        for tab in tabs:
            properties = tab["tabProperties"]
            add_sections(tab["documentTab"], properties["tabId"], properties.get("title"))
            visit(tab.get("childTabs", []))

    if document.get("tabs"):
        visit(document["tabs"])
    elif "body" in document:
        add_sections(document, None, None)
    else:
        raise ValueError("No body or tabs; fetch documents.get with includeTabsContent=true.")
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
            raise ValueError(f"Invalid JSON near character {error.pos}.") from error
        result = extract(document)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        sys.stderr.write(
            f"docs_text: Invalid or unreadable Docs input ({type(error).__name__}); fetch full tab content.\n"
        )
        return 1
    sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
