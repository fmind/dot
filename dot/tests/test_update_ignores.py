"""Exercise the ignore audit against disposable Git repositories."""

import importlib.util
import json
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2] / "skills/repository-maintenance/references/update-ignores/scripts/audit.py"
)


@pytest.fixture
def audit() -> ModuleType:
    spec = importlib.util.spec_from_file_location("update_ignores_audit", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    excludes = tmp_path / "global-ignore"
    excludes.write_text(".DS_Store\n.claude/\n")
    config = tmp_path / "gitconfig"
    config.write_text(f"[core]\n\texcludesFile = {excludes}\n")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    root = tmp_path / "repo"
    (root / "src/__pycache__").mkdir(parents=True)
    (root / "src/__pycache__/mod.cpython-314.pyc").write_bytes(b"")
    (root / "src/app.py").write_text("")
    (root / "uv.lock").write_text("")
    (root / "keep.log").write_text("")
    (root / ".venv").mkdir()
    (root / ".venv/.gitignore").write_text("*\n")
    (root / ".gitignore").write_text(
        "# Python\n__pycache__/\n.venv/\nnode_modules/\n__pycache__/\n.claude/\n*.log\n!keep.log\n"
    )
    (root / ".ignore").write_text("uv.lock\n__pycache__/\nmissing/\n")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "src/app.py", "uv.lock", "keep.log", ".gitignore"], check=True)
    return root


def statuses(report: dict, name: str) -> dict[int, tuple[str, list[str], int, int]]:
    (item,) = [entry for entry in report["files"] if entry["file"] == name]
    return {p["line"]: (p["status"], p["notes"], p["matches"], p["tracked"]) for p in item["patterns"]}


def test_gitignore_patterns_report_hits_shadowing_and_global_duplicates(audit: ModuleType, repository: Path) -> None:
    report = audit.audit(repository, [])

    assert [entry["file"] for entry in report["files"]] == [".gitignore"]  # tool-written .venv/.gitignore skipped
    lines = statuses(report, ".gitignore")
    assert lines[2] == ("unused", [], 0, 0)  # Git attributes each path to the last matching pattern
    assert lines[3][0] == "used"  # .venv/
    assert lines[4] == ("unused", [], 0, 0)  # node_modules/
    assert lines[5] == ("used", ["duplicate of line 2"], 1, 0)
    assert lines[6] == ("unused", ["also in global excludes"], 0, 0)
    assert lines[7][0] == "unused"  # *.log: the later negation decides keep.log
    assert lines[8] == ("used", [], 1, 1)  # !keep.log


def test_search_ignore_counts_tracked_hits_and_gitignore_shadowing(audit: ModuleType, repository: Path) -> None:
    lines = statuses(audit.audit(repository / "src", [repository / ".ignore"]), ".ignore")

    assert lines[1] == ("used", [], 1, 1)  # uv.lock
    assert lines[2][0] == "unused"  # __pycache__/: .gitignore already hides it from ripgrep
    assert lines[3][0] == "unused"  # missing/


def test_search_negations_are_never_reported_unused(audit: ModuleType, repository: Path) -> None:
    (repository / ".ignore").write_text("uv.lock\n!.venv/\n*.py\n!src/app.py\n")
    report = audit.audit(repository, [repository / ".ignore"])
    lines = statuses(report, ".ignore")
    note = "negation: re-includes for search; not measurable here"

    assert lines[2] == ("n/a", [note], 0, 0)  # re-includes a gitignored path: .gitignore wins in Git
    assert lines[4] == ("used", [note], 1, 1)  # refines an earlier .ignore pattern, so Git attributes it
    assert report["files"][0]["warnings"] == []
    assert statuses(audit.audit(repository, []), ".gitignore")[8][1] == []  # .gitignore negations stay measured


def test_nested_search_ignore_warns_about_root_anchoring(
    audit: ModuleType, repository: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repository / "src/.ignore").write_text("/app.py\n")
    (item,) = audit.audit(repository, [repository / "src/.ignore"])["files"]

    assert item["file"] == "src/.ignore"
    assert len(item["warnings"]) == 1
    assert "resolve against the repository root, not src/" in item["warnings"][0]
    assert audit.main(["--root", str(repository), str(repository / "src/.ignore")]) == 0
    assert "warning: nested .ignore" in capsys.readouterr().out


def test_cli_emits_json_and_fails_outside_a_repository(
    audit: ModuleType, repository: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert audit.main(["--root", str(repository), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["files"][0]["file"] == ".gitignore"

    outside = tmp_path / "outside"
    outside.mkdir()
    assert audit.main(["--root", str(outside)]) == 1
    assert "Ignore audit error: git rev-parse failed" in capsys.readouterr().err
