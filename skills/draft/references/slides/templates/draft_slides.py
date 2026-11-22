#!/usr/bin/env python3
"""Starter example: create or patch a native Google Slides deck via gws slides and verify read-back."""

from __future__ import annotations

import argparse
import json
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def _run_gws(args: list[str], *, cwd: Path) -> dict[str, Any]:
    gws = shutil.which("gws")
    if not gws:
        raise RuntimeError("gws binary not found on PATH; run `dot login workspace`.")
    proc = subprocess.run(  # noqa: S603
        [gws, *args, "--format", "json"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    if proc.returncode != 0:
        detail = " ".join((proc.stderr or proc.stdout).split())[-300:]
        raise RuntimeError(f"gws {' '.join(args[:3])} failed: {detail}")
    raw = proc.stdout.strip()
    idx = raw.find("{")
    if idx == -1:
        raise RuntimeError("gws did not return a JSON object.")
    parsed = json.loads(raw[idx:])
    if not isinstance(parsed, dict):
        raise RuntimeError("gws returned non-object JSON.")
    return parsed


def build_requests(slides: list[dict[str, Any]], *, prefix: str | None = None) -> list[dict[str, Any]]:
    """Build Slides batchUpdate requests with collision-safe objectIds for title + body slides."""
    token = prefix or secrets.token_hex(4)
    requests: list[dict[str, Any]] = []
    for index, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            raise ValueError(f"Slide {index} must be a JSON object.")
        title = str(slide.get("title", "")).strip()
        if not title:
            raise ValueError(f"Slide {index} requires a non-empty 'title'.")
        slide_id = f"s_{token}_{index:02d}"
        title_id = f"t_{token}_{index:02d}"
        body_id = f"b_{token}_{index:02d}"
        requests.append(
            {
                "createSlide": {
                    "objectId": slide_id,
                    "slideLayoutReference": {"predefinedLayout": "TITLE_AND_BODY"},
                    "placeholderIdMappings": [
                        {"layoutPlaceholder": {"type": "TITLE", "index": 0}, "objectId": title_id},
                        {"layoutPlaceholder": {"type": "BODY", "index": 0}, "objectId": body_id},
                    ],
                }
            }
        )
        requests.append({"insertText": {"objectId": title_id, "text": title}})
        if body := str(slide.get("body", "")).strip():
            requests.append({"insertText": {"objectId": body_id, "text": body}})
    return requests


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False, suggest_on_error=True)
    parser.add_argument("spec", type=Path, help="JSON file with {'title': str, 'slides': [{'title', 'body'}]} .")
    parser.add_argument("--presentation-id", default=None, help="Existing presentation ID to append slides to.")
    parser.add_argument("--export-pdf", type=Path, default=None, help="Optional path to export a verification PDF.")
    parser.add_argument("--dry-run", action="store_true", help="Print batchUpdate plan without writing.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
        if not isinstance(spec, dict):
            raise ValueError("Spec must be a JSON object with 'title' and 'slides'.")
        title = str(spec.get("title", "")).strip()
        slides = spec.get("slides")
        if not title or not isinstance(slides, list) or not slides:
            raise ValueError("Spec must contain non-empty 'title' and 'slides'.")
        requests = build_requests(slides)
        if args.dry_run:
            sys.stdout.write(
                json.dumps({"ok": True, "dry_run": True, "title": title, "requests": requests}, indent=2) + "\n"
            )
            return 0

        with tempfile.TemporaryDirectory(prefix="draft-slides-") as tmp:
            tmp_dir = Path(tmp)
            pres_id = args.presentation_id
            batch_body: dict[str, Any] = {"requests": requests}
            if pres_id:
                existing = _run_gws(
                    [
                        "slides",
                        "presentations",
                        "get",
                        "--params",
                        json.dumps({"presentationId": pres_id, "fields": "presentationId,revisionId"}),
                    ],
                    cwd=tmp_dir,
                )
                if revision_id := existing.get("revisionId"):
                    batch_body["writeControl"] = {"requiredRevisionId": str(revision_id)}
            else:
                created = _run_gws(
                    ["slides", "presentations", "create", "--json", json.dumps({"title": title})],
                    cwd=tmp_dir,
                )
                pres_id = str(created["presentationId"])
            _run_gws(
                [
                    "slides",
                    "presentations",
                    "batchUpdate",
                    "--params",
                    json.dumps({"presentationId": pres_id}),
                    "--json",
                    json.dumps(batch_body),
                ],
                cwd=tmp_dir,
            )
            verified = _run_gws(
                [
                    "slides",
                    "presentations",
                    "get",
                    "--params",
                    json.dumps({"presentationId": pres_id, "fields": "presentationId,title,slides(objectId)"}),
                ],
                cwd=tmp_dir,
            )
            if args.export_pdf:
                pdf_out = args.export_pdf.resolve()
                gws = shutil.which("gws") or "gws"
                proc = subprocess.run(  # noqa: S603
                    [
                        gws,
                        "drive",
                        "files",
                        "export",
                        "--params",
                        json.dumps({"fileId": pres_id, "mimeType": "application/pdf"}),
                        "--output",
                        str(pdf_out),
                    ],
                    cwd=tmp_dir,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=120,
                )
                if proc.returncode != 0:
                    raise RuntimeError(f"PDF export failed: {proc.stderr.strip()}")
            payload = {
                "ok": True,
                "presentationId": pres_id,
                "title": verified.get("title"),
                "slide_count": len(verified.get("slides") or []),
                "url": f"https://docs.google.com/presentation/d/{pres_id}/edit",
            }
            sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    except (
        OSError,
        KeyError,
        RuntimeError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
