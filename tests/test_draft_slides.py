"""Unit tests for the Google Slides drafting starter template."""

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

SCRIPT = ROOT / "skills/draft/references/slides/templates/draft_slides.py"


@pytest.fixture
def mod() -> ModuleType:
    return load_script("draft_slides_tpl", SCRIPT)


def _write_spec(tmp_path: Path, payload: dict[str, object]) -> Path:
    spec = tmp_path / "slides.json"
    spec.write_text(json.dumps(payload), encoding="utf-8")
    return spec


def test_dry_run_and_flag_validation(mod: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    spec = _write_spec(
        tmp_path,
        {"title": "Exec Review", "slides": [{"title": "Latency dropped 40%", "body": "P95 fell from 120ms to 72ms."}]},
    )
    assert mod.main([str(spec), "--drive-folder", "folder_abcd", "--dry-run"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert out["drive_folder"] == "folder_abcd"
    assert any("createSlide" in req for req in out["requests"])

    assert mod.main([str(spec), "--presentation-id", "pres_1234", "--drive-folder", "folder_abcd", "--dry-run"]) == 1
    assert "--drive-folder cannot be combined" in capsys.readouterr().err
    assert mod.main([str(spec), "--presentation-id", "bad/id", "--dry-run"]) == 1
    assert "Invalid --presentation-id" in capsys.readouterr().err

    # Null slide body is omitted rather than coerced to literal "None".
    null_body_spec = _write_spec(tmp_path, {"title": "Deck", "slides": [{"title": "Only title", "body": None}]})
    assert mod.main([str(null_body_spec), "--dry-run"]) == 0
    out_null = json.loads(capsys.readouterr().out)
    insert_texts = [req["insertText"]["text"] for req in out_null["requests"] if "insertText" in req]
    assert insert_texts == ["Only title"]

    # Symlink --export-pdf fails closed before invoking gws.
    target_file = tmp_path / "protected.txt"
    target_file.write_text("keep", encoding="utf-8")
    pdf_link = tmp_path / "export.pdf"
    pdf_link.symlink_to(target_file)
    assert mod.main([str(spec), "--export-pdf", str(pdf_link), "--dry-run"]) == 1
    assert "symlink" in capsys.readouterr().err
    assert target_file.read_text(encoding="utf-8") == "keep"


def test_create_deletes_default_blank_slide_moves_folder_and_exports_private_pdf(tmp_path: Path) -> None:
    spec = _write_spec(
        tmp_path,
        {
            "title": "Architecture Update",
            "slides": [
                {"title": "Decision: adopt unified queue", "body": "Cuts tail latency."},
                {"title": "Next steps", "body": "Roll out by Q2."},
            ],
        },
    )
    log_path = tmp_path / "gws-calls.jsonl"
    pdf_out = tmp_path / "out/deck.pdf"
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
        "if args[:3] == ['slides', 'presentations', 'create']:\n"
        "    print(json.dumps({'presentationId': 'pres_001', 'slides': [{'objectId': 'default_blank_0'}]}))\n"
        "elif args[:3] == ['drive', 'files', 'get']:\n"
        "    print(json.dumps({'parents': ['root_p']}))\n"
        "elif args[:3] == ['drive', 'files', 'update']:\n"
        "    print(json.dumps({'id': 'pres_001'}))\n"
        "elif args[:3] == ['slides', 'presentations', 'batchUpdate']:\n"
        "    body = json.loads(args[args.index('--json') + 1])\n"
        "    assert any(r.get('deleteObject', {}).get('objectId') == 'default_blank_0' for r in body['requests'])\n"
        "    created_ids = [r['createSlide']['objectId'] for r in body['requests'] if 'createSlide' in r]\n"
        "    (Path(os.environ['CALL_LOG']).parent / 'created_ids.json').write_text(json.dumps(created_ids), encoding='utf-8')\n"
        "    print(json.dumps({'presentationId': 'pres_001'}))\n"
        "elif args[:3] == ['slides', 'presentations', 'get']:\n"
        "    if os.environ.get('INJECT_API_ERR') == '1':\n"
        "        print(json.dumps({'error': {'code': 500, 'message': 'backend failure'}}))\n"
        "    elif os.environ.get('INJECT_API_ERR') == 'empty_slides':\n"
        "        print(json.dumps({'presentationId': 'pres_001', 'title': 'Architecture Update', 'slides': []}))\n"
        "    else:\n"
        "        ids_file = Path(os.environ['CALL_LOG']).parent / 'created_ids.json'\n"
        "        ids = json.loads(ids_file.read_text(encoding='utf-8')) if ids_file.is_file() else ['s1', 's2']\n"
        "        print(json.dumps({'presentationId': 'pres_001', 'title': 'Architecture Update', 'slides': [{'objectId': i} for i in ids]}))\n"
        "elif args[:3] == ['drive', 'files', 'export']:\n"
        "    out_name = args[args.index('--output') + 1]\n"
        "    assert '/' not in out_name, f'export must stage inside cwd: {out_name}'\n"
        "    (cwd / out_name).write_bytes(b'%PDF-1.7\\n%mock\\n')\n"
        "else:\n"
        "    print(json.dumps({'ok': True}))\n",
        encoding="utf-8",
    )
    fake_gws.chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "CALL_LOG": str(log_path)}

    res = subprocess.run(
        [
            sys.executable,
            "-I",
            str(SCRIPT),
            str(spec),
            "--drive-folder",
            "folder_7777",
            "--export-pdf",
            str(pdf_out),
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert res.returncode == 0, res.stderr
    result = json.loads(res.stdout)
    assert result["presentationId"] == "pres_001"
    assert result["slide_count"] == 2
    assert pdf_out.is_file()
    assert stat.S_IMODE(pdf_out.stat().st_mode) == 0o600
    calls = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert any(c[:3] == ["drive", "files", "update"] and "folder_7777" in " ".join(c) for c in calls)

    res_err = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(spec)],
        env={**env, "INJECT_API_ERR": "1"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert res_err.returncode == 1
    assert "API error" in res_err.stderr

    bad_pdf = tmp_path / "out/should-not-exist.pdf"
    res_empty = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(spec), "--export-pdf", str(bad_pdf)],
        env={**env, "INJECT_API_ERR": "empty_slides"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert res_empty.returncode == 1
    assert "slide count mismatch" in res_empty.stderr
    assert not bad_pdf.exists()
