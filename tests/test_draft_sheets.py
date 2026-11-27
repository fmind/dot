"""Unit tests for the Google Sheets drafting starter template."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

from repo_helpers import ROOT, load_script

SCRIPT = ROOT / "skills/draft/references/sheets/templates/draft_sheets.py"


@pytest.fixture
def mod() -> ModuleType:
    return load_script("draft_sheets_tpl", SCRIPT)


def _write_spec(tmp_path: Path, payload: dict[str, object]) -> Path:
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps(payload), encoding="utf-8")
    return spec


def test_dry_run_validates_spec_and_drive_folder(
    mod: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    spec = _write_spec(
        tmp_path,
        {
            "title": "Q4 KPI Summary",
            "sheet": "Summary",
            "rows": [["Metric", "Value"], ["Latency", 42]],
            "formulas": [{"range": "'Summary'!B3", "values": [["=SUM(B2:B2)"]]}],
        },
    )
    assert mod.main([str(spec), "--drive-folder", "1AbCdEfGhIjKlMnOp", "--dry-run"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert out["dry_run"] is True
    assert out["range"] == "'Summary'!A1:B2"
    assert out["data_value_input"] == "RAW"
    assert out["drive_folder"] == "1AbCdEfGhIjKlMnOp"


def test_rejects_conflicting_folder_and_invalid_folder_id(
    mod: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    spec = _write_spec(tmp_path, {"title": "T", "sheet": "S", "rows": [["A"], [1]]})
    assert mod.main([str(spec), "--spreadsheet-id", "sheet1234", "--drive-folder", "folder1234", "--dry-run"]) == 1
    assert "--drive-folder cannot be combined" in capsys.readouterr().err
    assert mod.main([str(spec), "--drive-folder", "bad/id", "--dry-run"]) == 1
    assert "Invalid --drive-folder" in capsys.readouterr().err
    assert mod.main([str(spec), "--spreadsheet-id", "bad/id", "--dry-run"]) == 1
    assert "Invalid --spreadsheet-id" in capsys.readouterr().err

    null_spec = _write_spec(tmp_path, {"title": None, "sheet": "S", "rows": [["A"], [1]]})
    assert mod.main([str(null_spec), "--dry-run"]) == 1
    assert "non-empty string" in capsys.readouterr().err

    # Falsy non-list formulas and 1D formula values must fail closed.
    bad_formulas = _write_spec(tmp_path, {"title": "T", "sheet": "S", "rows": [["A"], [1]], "formulas": {}})
    assert mod.main([str(bad_formulas), "--dry-run"]) == 1
    assert "'formulas' must be a list" in capsys.readouterr().err
    bad_1d = _write_spec(
        tmp_path,
        {"title": "T", "sheet": "S", "rows": [["A"], [1]], "formulas": [{"range": "S!A3", "values": ["=SUM(A2)"]}]},
    )
    assert mod.main([str(bad_1d), "--dry-run"]) == 1
    assert "'formulas' must be a list" in capsys.readouterr().err


def test_find_formula_errors_catches_num_and_other_tokens(mod: ModuleType) -> None:
    assert mod.find_formula_errors([["ok", "#NUM!"], ["#DIV/0!", "42"]]) == ["R1C2:#NUM!", "R2C1:#DIV/0!"]
    assert mod.col_label(1) == "A"
    assert mod.col_label(27) == "AA"


def test_create_flow_writes_env_sentinel_moves_folder_and_verifies_rows(tmp_path: Path) -> None:
    spec = _write_spec(
        tmp_path,
        {
            "title": "Budget",
            "sheet": "Summary",
            "rows": [["Item", "Cost"], ["Compute", 100]],
            "formulas": [{"range": "'Summary'!A1:B2", "values": [["Item", "Cost"], ["Compute", 100]]}],
        },
    )
    log_path = tmp_path / "gws-calls.jsonl"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_gws = bin_dir / "gws"
    fake_gws.write_text(
        f"#!{sys.executable}\n"
        "import json, os, stat, sys\n"
        "from pathlib import Path\n"
        "cwd = Path.cwd()\n"
        "env_file = cwd / '.env'\n"
        "assert env_file.is_file(), 'missing .env sentinel'\n"
        "assert stat.S_IMODE(env_file.stat().st_mode) == 0o600\n"
        "args = sys.argv[1:]\n"
        "with Path(os.environ['CALL_LOG']).open('a', encoding='utf-8') as f:\n"
        "    f.write(json.dumps(args) + '\\n')\n"
        "if args[:3] == ['sheets', 'spreadsheets', 'create']:\n"
        "    if os.environ.get('INJECT_ERR') == 'empty_sheets':\n"
        "        print(json.dumps({'spreadsheetId': 'ss_001', 'sheets': []}))\n"
        "    else:\n"
        "        print(json.dumps({'spreadsheetId': 'ss_001', 'sheets': [{'properties': {'sheetId': 0}}]}))\n"
        "elif args[:3] == ['drive', 'files', 'get']:\n"
        "    print(json.dumps({'parents': ['root_parent']}))\n"
        "elif args[:3] == ['drive', 'files', 'update']:\n"
        "    print(json.dumps({'id': 'ss_001'}))\n"
        "elif args[:4] == ['sheets', 'spreadsheets', 'values', 'batchGet']:\n"
        "    if os.environ.get('INJECT_ERR') == 'api':\n"
        "        print(json.dumps({'error': {'code': 403, 'message': 'forbidden'}}))\n"
        "    elif os.environ.get('INJECT_ERR') == 'num':\n"
        "        print(json.dumps({'valueRanges': [{'values': [['Item', 'Cost'], ['Compute', '#NUM!']]}]}))\n"
        "    elif os.environ.get('INJECT_ERR') == 'empty_ranges':\n"
        "        print(json.dumps({'valueRanges': []}))\n"
        "    else:\n"
        "        print(json.dumps({'valueRanges': [{'values': [['Item', 'Cost'], ['Compute', '100']]}]}))\n"
        "else:\n"
        "    print(json.dumps({'ok': True}))\n",
        encoding="utf-8",
    )
    fake_gws.chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "CALL_LOG": str(log_path)}

    res = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(spec), "--drive-folder", "folder_9999"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["spreadsheetId"] == "ss_001"
    assert data["rows_verified"] == 2
    calls = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert any(c[:3] == ["drive", "files", "update"] and "folder_9999" in " ".join(c) for c in calls)

    res_api = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(spec)],
        env={**env, "INJECT_ERR": "api"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert res_api.returncode == 1
    assert "API error" in res_api.stderr

    res_num = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(spec)],
        env={**env, "INJECT_ERR": "num"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert res_num.returncode == 1
    assert "#NUM!" in res_num.stderr

    res_empty = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(spec)],
        env={**env, "INJECT_ERR": "empty_ranges"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert res_empty.returncode == 1
    assert "valueRanges" in res_empty.stderr

    res_no_sheets = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(spec)],
        env={**env, "INJECT_ERR": "empty_sheets"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert res_no_sheets.returncode == 1
    assert "sheet metadata" in res_no_sheets.stderr
    assert stat.S_ISREG(SCRIPT.stat().st_mode)
