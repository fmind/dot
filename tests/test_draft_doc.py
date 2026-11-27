"""Contract tests for lean draft-* starter scripts (draft_slides, draft_sheets)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from repo_helpers import ROOT, load_script

DRAFT_SLIDES = ROOT / "skills/draft/references/slides/templates/draft_slides.py"
DRAFT_SHEETS = ROOT / "skills/draft/references/sheets/templates/draft_sheets.py"


def _run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", str(script), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def test_draft_slides_starter_builds_unique_ids_and_write_control(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec_file = tmp_path / "deck.json"
    spec_file.write_text(
        json.dumps(
            {
                "title": "Q4 Architecture Review",
                "slides": [
                    {"title": "Option B cuts latency 40%", "body": "Measured over n=1,000 requests."},
                    {"title": "Next step: migrate staging", "body": "Target date: 2026-12-01."},
                ],
            }
        ),
        encoding="utf-8",
    )
    res = _run(DRAFT_SLIDES, str(spec_file), "--dry-run")
    assert res.returncode == 0, res.stderr
    plan = json.loads(res.stdout)
    assert plan["ok"] is True
    assert plan["dry_run"] is True
    assert plan["title"] == "Q4 Architecture Review"
    assert len(plan["requests"]) == 6
    assert plan["requests"][0]["createSlide"]["objectId"].startswith("s_")
    assert plan["requests"][0]["createSlide"]["objectId"].endswith("_01")

    # Appending to an existing presentation passes writeControl.requiredRevisionId.
    mod = load_script("draft_slides", DRAFT_SLIDES)
    batch_payloads: list[dict[str, Any]] = []

    def fake_gws(args: list[str], *, cwd: Path) -> dict[str, object]:
        assert cwd.is_dir()
        if args[:3] == ["slides", "presentations", "get"]:
            params = json.loads(args[args.index("--params") + 1])
            if "revisionId" in params["fields"]:
                return {"presentationId": "pres_1", "revisionId": "rev_42", "slides": [{"objectId": "p1"}]}
            created_ids = [
                req["createSlide"]["objectId"]
                for req in batch_payloads[-1]["requests"]
                if isinstance(req, dict) and "createSlide" in req
            ]
            return {
                "presentationId": "pres_1",
                "title": "Existing Deck",
                "slides": [{"objectId": "p1"}, *({"objectId": oid} for oid in created_ids)],
            }
        if args[:3] == ["slides", "presentations", "batchUpdate"]:
            batch_payloads.append(json.loads(args[args.index("--json") + 1]))
            return {"presentationId": "pres_1"}
        raise AssertionError(f"Unexpected call: {args}")

    monkeypatch.setattr(mod, "_run_gws", fake_gws)
    assert mod.main([str(spec_file), "--presentation-id", "pres_1"]) == 0
    assert batch_payloads[0]["writeControl"] == {"requiredRevisionId": "rev_42"}

    # Empty slide title fails closed.
    bad_spec = tmp_path / "bad.json"
    bad_spec.write_text(json.dumps({"title": "Deck", "slides": [{"title": "  "}]}), encoding="utf-8")
    assert _run(DRAFT_SLIDES, str(bad_spec), "--dry-run").returncode == 1


def test_draft_sheets_starter_validates_rows_splits_formulas_and_resolves_sheet_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec_file = tmp_path / "budget.json"
    spec_file.write_text(
        json.dumps(
            {
                "title": "Cloud Cost Model",
                "sheet": "2026 Summary",
                "rows": [
                    ["Service", "Monthly USD"],
                    ["Cloud Run", 420],
                    ["BigQuery", 180],
                ],
                "formulas": [{"range": "'2026 Summary'!B4", "values": [["=SUM(B2:B3)"]]}],
            }
        ),
        encoding="utf-8",
    )
    res = _run(DRAFT_SHEETS, str(spec_file), "--dry-run")
    assert res.returncode == 0, res.stderr
    plan = json.loads(res.stdout)
    assert plan["ok"] is True
    assert plan["range"] == "'2026 Summary'!A1:B3"
    assert plan["data_value_input"] == "RAW"
    assert plan["formula_ranges"] == 1

    # Ragged rows fail closed.
    ragged = tmp_path / "ragged.json"
    ragged.write_text(json.dumps({"title": "Bad", "sheet": "S", "rows": [["A", "B"], ["only-one"]]}), encoding="utf-8")
    assert _run(DRAFT_SHEETS, str(ragged), "--dry-run").returncode == 1

    mod = load_script("draft_sheets", DRAFT_SHEETS)
    assert mod.col_label(1) == "A"
    assert mod.col_label(26) == "Z"
    assert mod.col_label(27) == "AA"
    assert mod.find_formula_errors([["Total", "600"]]) == []
    assert mod.find_formula_errors([["Total", "#REF!"], ["Ratio", "#DIV/0!"]]) == ["R1C2:#REF!", "R2C2:#DIV/0!"]

    # Updating an existing spreadsheet resolves the target tab's real sheetId instead of hardcoding 0.
    seen_formats: list[dict[str, Any]] = []
    seen_value_modes: list[str] = []

    def fake_sheets_gws(args: list[str], *, cwd: Path) -> dict[str, object]:
        assert cwd.is_dir()
        if args[:3] == ["sheets", "spreadsheets", "get"]:
            return {
                "sheets": [
                    {"properties": {"sheetId": 10, "title": "Other"}},
                    {"properties": {"sheetId": 99, "title": "2026 Summary"}},
                ]
            }
        if args[:4] == ["sheets", "spreadsheets", "values", "batchUpdate"]:
            body = json.loads(args[args.index("--json") + 1])
            seen_value_modes.append(body["valueInputOption"])
            return {"totalUpdatedCells": 6}
        if args[:3] == ["sheets", "spreadsheets", "batchUpdate"]:
            seen_formats.append(json.loads(args[args.index("--json") + 1]))
            return {}
        if args[:4] == ["sheets", "spreadsheets", "values", "batchGet"]:
            params = json.loads(args[args.index("--params") + 1])
            assert params["ranges"] == ["'2026 Summary'!A1:B3", "'2026 Summary'!B4"]
            return {
                "valueRanges": [
                    {"values": [["Service", "Monthly USD"], ["Cloud Run", "420"], ["BigQuery", "180"]]},
                    {"values": [["600"]]},
                ]
            }
        raise AssertionError(f"Unexpected call: {args}")

    monkeypatch.setattr(mod, "_run_gws", fake_sheets_gws)
    assert mod.main([str(spec_file), "--spreadsheet-id", "sheet_abc123"]) == 0
    assert seen_value_modes == ["RAW", "USER_ENTERED"]
    assert seen_formats[0]["requests"][0]["updateSheetProperties"]["properties"]["sheetId"] == 99

    # Formula errors outside the RAW data range must still fail read-back verification.
    def bad_formula_gws(args: list[str], *, cwd: Path) -> dict[str, object]:
        if args[:4] == ["sheets", "spreadsheets", "values", "batchGet"]:
            return {
                "valueRanges": [
                    {"values": [["Service", "Monthly USD"], ["Cloud Run", "420"], ["BigQuery", "180"]]},
                    {"values": [["#REF!"]]},
                ]
            }
        return fake_sheets_gws(args, cwd=cwd)

    monkeypatch.setattr(mod, "_run_gws", bad_formula_gws)
    assert mod.main([str(spec_file), "--spreadsheet-id", "sheet_abc123"]) == 1

    # Malformed formulas entries fail closed before calling gws.
    bad_formulas = tmp_path / "bad_formulas.json"
    bad_formulas.write_text(
        json.dumps({"title": "Bad", "sheet": "S", "rows": [["A"]], "formulas": [{"range": "", "values": []}]}),
        encoding="utf-8",
    )
    assert _run(DRAFT_SHEETS, str(bad_formulas), "--dry-run").returncode == 1
