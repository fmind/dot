#!/usr/bin/env python3
"""Starter example: create or patch a native Google Slides deck via gws slides and verify read-back."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any

DRIVE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{4,128}$")


def _run_gws(args: list[str], *, cwd: Path) -> dict[str, Any]:
    gws = shutil.which("gws")
    if not gws:
        raise RuntimeError("gws binary not found on PATH; run `dot login workspace`.")
    proc = subprocess.run(  # noqa: S603
        [gws, *args, "--format", "json"],
        cwd=cwd,
        stdin=subprocess.DEVNULL,
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
    if "error" in parsed:
        detail = json.dumps(parsed["error"], ensure_ascii=False)[:300]
        raise RuntimeError(f"gws {' '.join(args[:3])} API error: {detail}")
    return parsed


def _move_to_folder(file_id: str, folder_id: str, *, cwd: Path) -> None:
    meta = _run_gws(
        [
            "drive",
            "files",
            "get",
            "--params",
            json.dumps({"fileId": file_id, "fields": "parents", "supportsAllDrives": True}),
        ],
        cwd=cwd,
    )
    params: dict[str, Any] = {"fileId": file_id, "addParents": folder_id, "supportsAllDrives": True}
    previous_parents = [str(p) for p in (meta.get("parents") or []) if str(p) != folder_id]
    if previous_parents:
        params["removeParents"] = ",".join(previous_parents)
    _run_gws(["drive", "files", "update", "--params", json.dumps(params)], cwd=cwd)


def _validate_drive_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not DRIVE_ID_RE.fullmatch(value.strip()):
        raise ValueError(f"Invalid {label}: {value!r}")
    return value.strip()


def _validate_export_pdf_path(path: Path) -> Path:
    if path.is_symlink():
        raise ValueError(f"Refusing to overwrite symlink --export-pdf path: {path}")
    if path.exists() and path.is_dir():
        raise ValueError(f"--export-pdf must be a file path, not a directory: {path}")
    resolved_parent = path.parent.resolve()
    target = resolved_parent / path.name
    if target.is_symlink():
        raise ValueError(f"Refusing to overwrite symlink --export-pdf path: {target}")
    if target.exists() and target.is_dir():
        raise ValueError(f"--export-pdf must be a file path, not a directory: {target}")
    return target


def _atomic_copy_to(src: Path, dst: Path) -> None:
    if dst.is_symlink():
        raise ValueError(f"Refusing to overwrite symlink target: {dst}")
    if dst.exists() and dst.is_dir():
        raise ValueError(f"Refusing to overwrite directory target: {dst}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{dst.name}.", suffix=".tmp", dir=dst.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as out_f, src.open("rb") as in_f:
            shutil.copyfileobj(in_f, out_f)
            out_f.flush()
            os.fchmod(out_f.fileno(), 0o600)
            os.fsync(out_f.fileno())
        if dst.is_symlink():
            raise ValueError(f"Refusing to overwrite symlink target: {dst}")
        tmp_path.replace(dst)
    except BaseException:
        with suppress(OSError):
            tmp_path.unlink()
        raise


def build_requests(slides: list[dict[str, Any]], *, prefix: str | None = None) -> list[dict[str, Any]]:
    """Build Slides batchUpdate requests with collision-safe objectIds for title + body slides."""
    token = prefix or secrets.token_hex(4)
    requests: list[dict[str, Any]] = []
    for index, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            raise ValueError(f"Slide {index} must be a JSON object.")
        raw_title = slide.get("title")
        if not isinstance(raw_title, str) or not raw_title.strip():
            raise ValueError(f"Slide {index} requires a non-empty string 'title'.")
        title = raw_title.strip()
        raw_body = slide.get("body")
        if raw_body is not None and not isinstance(raw_body, str):
            raise ValueError(f"Slide {index} 'body' must be a string when provided.")
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
        if isinstance(raw_body, str) and (body := raw_body.strip()):
            requests.append({"insertText": {"objectId": body_id, "text": body}})
    return requests


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        allow_abbrev=False,
    )
    if hasattr(parser, "suggest_on_error"):
        parser.suggest_on_error = True
    parser.add_argument("spec", type=Path, help="JSON file with {'title': str, 'slides': [{'title', 'body'}]} .")
    parser.add_argument("--presentation-id", default=None, help="Existing presentation ID to append slides to.")
    parser.add_argument("--drive-folder", default=None, help="Target Drive folder ID when creating a presentation.")
    parser.add_argument("--export-pdf", type=Path, default=None, help="Optional path to export a verification PDF.")
    parser.add_argument("--dry-run", action="store_true", help="Print batchUpdate plan without writing.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        pres_id = (
            _validate_drive_id(args.presentation_id, "--presentation-id") if args.presentation_id is not None else None
        )
        drive_folder = None
        if args.drive_folder is not None:
            if pres_id is not None:
                raise ValueError("--drive-folder cannot be combined with --presentation-id.")
            drive_folder = _validate_drive_id(args.drive_folder, "--drive-folder")
        pdf_out = _validate_export_pdf_path(args.export_pdf) if args.export_pdf is not None else None
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
        if not isinstance(spec, dict):
            raise ValueError("Spec must be a JSON object with 'title' and 'slides'.")
        raw_title = spec.get("title")
        slides = spec.get("slides")
        if not isinstance(raw_title, str) or not raw_title.strip() or not isinstance(slides, list) or not slides:
            raise ValueError("Spec must contain non-empty string 'title' and non-empty 'slides'.")
        title = raw_title.strip()
        requests = build_requests(slides)
        if args.dry_run:
            plan: dict[str, Any] = {"ok": True, "dry_run": True, "title": title, "requests": requests}
            if drive_folder:
                plan["drive_folder"] = drive_folder
            sys.stdout.write(json.dumps(plan, indent=2) + "\n")
            return 0

        with tempfile.TemporaryDirectory(prefix="draft-slides-") as tmp:
            tmp_dir = Path(tmp)
            # Sentinel stops gws from walking upward into /tmp/.env or $TMPDIR/.env.
            os.close(os.open(tmp_dir / ".env", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
            batch_requests = list(requests)
            batch_body: dict[str, Any] = {"requests": batch_requests}
            expected_new_ids = {
                req["createSlide"]["objectId"]
                for req in requests
                if "createSlide" in req and isinstance(req["createSlide"].get("objectId"), str)
            }
            if pres_id:
                existing = _run_gws(
                    [
                        "slides",
                        "presentations",
                        "get",
                        "--params",
                        json.dumps({"presentationId": pres_id, "fields": "presentationId,revisionId,slides(objectId)"}),
                    ],
                    cwd=tmp_dir,
                )
                existing_slides = existing.get("slides")
                if existing_slides is not None and not isinstance(existing_slides, list):
                    raise RuntimeError("Existing presentation response contained invalid 'slides' field.")
                prior_slide_count = len(existing_slides or [])
                if revision_id := existing.get("revisionId"):
                    batch_body["writeControl"] = {"requiredRevisionId": str(revision_id)}
            else:
                prior_slide_count = 0
                created = _run_gws(
                    ["slides", "presentations", "create", "--json", json.dumps({"title": title})],
                    cwd=tmp_dir,
                )
                pres_id = _validate_drive_id(created.get("presentationId"), "API presentationId")
                batch_requests.extend(
                    {"deleteObject": {"objectId": str(oid)}}
                    for default_slide in created.get("slides") or []
                    if isinstance(default_slide, dict) and (oid := default_slide.get("objectId"))
                )
                if drive_folder:
                    _move_to_folder(pres_id, drive_folder, cwd=tmp_dir)
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
            if verified.get("presentationId") != pres_id:
                raise RuntimeError(
                    f"Read-back presentationId mismatch: expected {pres_id!r}, got {verified.get('presentationId')!r}."
                )
            verified_slides = verified.get("slides")
            if not isinstance(verified_slides, list):
                raise RuntimeError("Read-back response missing 'slides' list.")
            expected_total = prior_slide_count + len(slides)
            if len(verified_slides) != expected_total:
                raise RuntimeError(
                    f"Read-back slide count mismatch: expected {expected_total}, got {len(verified_slides)}."
                )
            returned_ids = {
                s.get("objectId") for s in verified_slides if isinstance(s, dict) and isinstance(s.get("objectId"), str)
            }
            if missing_ids := sorted(expected_new_ids - returned_ids):
                raise RuntimeError(f"Read-back missing created slide objectIds: {', '.join(missing_ids)}.")
            if pdf_out is not None:
                staged_pdf = tmp_dir / "export.pdf"
                gws = shutil.which("gws")
                if not gws:
                    raise RuntimeError("gws binary not found on PATH; run `dot login workspace`.")
                proc = subprocess.run(  # noqa: S603
                    [
                        gws,
                        "drive",
                        "files",
                        "export",
                        "--params",
                        json.dumps({"fileId": pres_id, "mimeType": "application/pdf"}),
                        "--output",
                        staged_pdf.name,
                    ],
                    cwd=tmp_dir,
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=120,
                )
                if proc.returncode != 0 or not staged_pdf.is_file() or staged_pdf.stat().st_size == 0:
                    detail = " ".join((proc.stderr or proc.stdout).split())[-300:]
                    raise RuntimeError(f"PDF export failed: {detail or 'output missing or empty'}")
                _atomic_copy_to(staged_pdf, pdf_out)
            payload = {
                "ok": True,
                "presentationId": pres_id,
                "title": verified.get("title"),
                "slide_count": len(verified_slides),
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
