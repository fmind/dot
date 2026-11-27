#!/usr/bin/env python3
"""Starter example: create or update a Google Sheet via gws sheets (RAW data + optional explicit formulas)."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SHEET_ERRORS = frozenset({"#REF!", "#NAME?", "#VALUE!", "#DIV/0!", "#N/A", "#NUM!", "#ERROR!"})
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


def col_label(col_count: int) -> str:
    """Convert a 1-based column index to an A1 column label (1 -> A, 27 -> AA)."""
    if col_count < 1:
        raise ValueError("col_count must be >= 1.")
    chars: list[str] = []
    n = col_count
    while n > 0:
        n, rem = divmod(n - 1, 26)
        chars.append(chr(ord("A") + rem))
    return "".join(reversed(chars))


def find_formula_errors(rows: list[list[Any]]) -> list[str]:
    """Return R#C# locations for any Google Sheets error token in read-back values."""
    errors: list[str] = []
    for row_idx, row in enumerate(rows, start=1):
        for col_idx, cell in enumerate(row, start=1):
            if isinstance(cell, str) and cell.strip() in SHEET_ERRORS:
                errors.append(f"R{row_idx}C{col_idx}:{cell.strip()}")
    return errors


def _resolve_sheet_id(spreadsheet_id: str, sheet_name: str, *, cwd: Path) -> int:
    meta = _run_gws(
        [
            "sheets",
            "spreadsheets",
            "get",
            "--params",
            json.dumps({"spreadsheetId": spreadsheet_id, "fields": "sheets.properties(sheetId,title)"}),
        ],
        cwd=cwd,
    )
    for sheet in meta.get("sheets") or []:
        props = sheet.get("properties") if isinstance(sheet, dict) else None
        if isinstance(props, dict) and props.get("title") == sheet_name:
            return int(props["sheetId"])
    raise ValueError(f"Sheet tab {sheet_name!r} not found in spreadsheet {spreadsheet_id}.")


def _format_requests(sheet_id: int, col_count: int) -> list[dict[str, Any]]:
    return [
        {
            "updateSheetProperties": {
                "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
                "fields": "gridProperties.frozenRowCount",
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": col_count,
                },
                "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                "fields": "userEnteredFormat.textFormat.bold",
            }
        },
        {
            "autoResizeDimensions": {
                "dimensions": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": col_count}
            }
        },
    ]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        allow_abbrev=False,
    )
    if hasattr(parser, "suggest_on_error"):
        parser.suggest_on_error = True
    parser.add_argument(
        "spec",
        type=Path,
        help="JSON file with {'title', 'sheet', 'rows': [[...]], 'formulas'?: [{'range', 'values'}], 'locale'?}.",
    )
    parser.add_argument("--spreadsheet-id", default=None, help="Existing spreadsheet ID to update.")
    parser.add_argument("--drive-folder", default=None, help="Target Drive folder ID when creating a new spreadsheet.")
    parser.add_argument("--dry-run", action="store_true", help="Validate spec and print payload without writing.")
    return parser


def _validate_drive_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not DRIVE_ID_RE.fullmatch(value.strip()):
        raise ValueError(f"Invalid {label}: {value!r}")
    return value.strip()


def _require_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Spec field {field!r} must be a non-empty string.")
    return value.strip()


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        spreadsheet_id = (
            _validate_drive_id(args.spreadsheet_id, "--spreadsheet-id") if args.spreadsheet_id is not None else None
        )
        drive_folder = None
        if args.drive_folder is not None:
            if spreadsheet_id is not None:
                raise ValueError("--drive-folder cannot be combined with --spreadsheet-id.")
            drive_folder = _validate_drive_id(args.drive_folder, "--drive-folder")
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
        if not isinstance(spec, dict):
            raise ValueError("Spec must be a JSON object.")
        title = _require_str(spec.get("title"), "title")
        sheet_name = _require_str(spec.get("sheet", "Summary"), "sheet")
        locale = _require_str(spec.get("locale", "en_US"), "locale")
        rows = spec.get("rows")
        if (
            not isinstance(rows, list)
            or not rows
            or not all(isinstance(row, list) and len(row) == len(rows[0]) for row in rows)
            or not rows[0]
        ):
            raise ValueError("Spec must include non-empty rectangular 'rows'.")
        raw_formulas = spec.get("formulas")
        formulas = [] if raw_formulas is None else raw_formulas
        if not isinstance(formulas, list) or not all(
            isinstance(entry, dict)
            and isinstance(entry.get("range"), str)
            and entry["range"].strip()
            and isinstance(entry.get("values"), list)
            and bool(entry["values"])
            and all(isinstance(row, list) for row in entry["values"])
            for entry in formulas
        ):
            raise ValueError("'formulas' must be a list of {'range', 'values': [[...]]} entries.")
        col_count = len(rows[0])
        end_col = col_label(col_count)
        quoted_sheet = "'" + sheet_name.replace("'", "''") + "'"
        write_range = f"{quoted_sheet}!A1:{end_col}{len(rows)}"

        if args.dry_run:
            plan: dict[str, Any] = {
                "ok": True,
                "dry_run": True,
                "title": title,
                "sheet": sheet_name,
                "range": write_range,
                "row_count": len(rows),
                "col_count": col_count,
                "data_value_input": "RAW",
                "formula_ranges": len(formulas),
            }
            if drive_folder:
                plan["drive_folder"] = drive_folder
            sys.stdout.write(json.dumps(plan, indent=2) + "\n")
            return 0

        with tempfile.TemporaryDirectory(prefix="draft-sheets-") as tmp:
            tmp_dir = Path(tmp)
            # Sentinel stops gws from walking upward into /tmp/.env or $TMPDIR/.env.
            os.close(os.open(tmp_dir / ".env", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
            if spreadsheet_id:
                sheet_id = _resolve_sheet_id(spreadsheet_id, sheet_name, cwd=tmp_dir)
            else:
                created = _run_gws(
                    [
                        "sheets",
                        "spreadsheets",
                        "create",
                        "--json",
                        json.dumps(
                            {
                                "properties": {"title": title, "locale": locale},
                                "sheets": [{"properties": {"sheetId": 0, "title": sheet_name}}],
                            }
                        ),
                    ],
                    cwd=tmp_dir,
                )
                spreadsheet_id = _validate_drive_id(created.get("spreadsheetId"), "API spreadsheetId")
                created_sheets = created.get("sheets")
                if (
                    not isinstance(created_sheets, list)
                    or not created_sheets
                    or not isinstance(created_sheets[0], dict)
                ):
                    raise RuntimeError("Create response missing sheet metadata.")
                sheet_id = int(created_sheets[0]["properties"]["sheetId"])
                if drive_folder:
                    _move_to_folder(spreadsheet_id, drive_folder, cwd=tmp_dir)

            # Write data cells with RAW to prevent formula injection from untrusted text.
            _run_gws(
                [
                    "sheets",
                    "spreadsheets",
                    "values",
                    "batchUpdate",
                    "--params",
                    json.dumps({"spreadsheetId": spreadsheet_id}),
                    "--json",
                    json.dumps({"valueInputOption": "RAW", "data": [{"range": write_range, "values": rows}]}),
                ],
                cwd=tmp_dir,
            )
            if formulas:
                _run_gws(
                    [
                        "sheets",
                        "spreadsheets",
                        "values",
                        "batchUpdate",
                        "--params",
                        json.dumps({"spreadsheetId": spreadsheet_id}),
                        "--json",
                        json.dumps({"valueInputOption": "USER_ENTERED", "data": formulas}),
                    ],
                    cwd=tmp_dir,
                )
            _run_gws(
                [
                    "sheets",
                    "spreadsheets",
                    "batchUpdate",
                    "--params",
                    json.dumps({"spreadsheetId": spreadsheet_id}),
                    "--json",
                    json.dumps({"requests": _format_requests(sheet_id, col_count)}),
                ],
                cwd=tmp_dir,
            )
            verify_ranges = list(dict.fromkeys([write_range, *(str(f["range"]).strip() for f in formulas)]))
            read_back = _run_gws(
                [
                    "sheets",
                    "spreadsheets",
                    "values",
                    "batchGet",
                    "--params",
                    json.dumps(
                        {
                            "spreadsheetId": spreadsheet_id,
                            "ranges": verify_ranges,
                            "valueRenderOption": "FORMATTED_VALUE",
                        }
                    ),
                ],
                cwd=tmp_dir,
            )
            value_ranges = read_back.get("valueRanges")
            if not isinstance(value_ranges, list) or len(value_ranges) != len(verify_ranges):
                raise RuntimeError(
                    f"Read-back returned {len(value_ranges) if isinstance(value_ranges, list) else 'invalid'} "
                    f"valueRanges, expected {len(verify_ranges)}."
                )
            all_returned_rows = [
                row
                for vr in value_ranges
                if isinstance(vr, dict)
                for row in (vr.get("values") or [])
                if isinstance(row, list)
            ]
            if errors := find_formula_errors(all_returned_rows):
                raise RuntimeError(f"Read-back detected spreadsheet formula errors: {', '.join(errors)}")
            primary_rows = (
                [row for row in (value_ranges[0].get("values") or []) if isinstance(row, list)]
                if isinstance(value_ranges[0], dict)
                else []
            )
            if len(primary_rows) != len(rows):
                raise RuntimeError(f"Read-back row count mismatch: expected {len(rows)}, got {len(primary_rows)}.")
            payload = {
                "ok": True,
                "spreadsheetId": spreadsheet_id,
                "title": title,
                "rows_verified": len(primary_rows),
                "url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit",
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
