"""Exercise the Typst 16:9 slide deck compiler and safe Google Drive uploader."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "skills/draft-typst-deck/scripts/build_typst_deck.py"


@pytest.fixture
def mod() -> ModuleType:
    spec = importlib.util.spec_from_file_location("build_typst_deck", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_scan_typst_escaping_issues_accepts_clean_syntax(mod: ModuleType) -> None:
    source = (
        '// Comment mentioning "\\$" and `\\~` is ignored\n'
        "/* Nested /* block \\$ */ comment */\n"
        '#let note = "Cost stays ~5.81 $ per run (escaped quote \\"ok\\")"\n'
        "#let badge = `EUR 0.42 ~ 5% *ok*`\n"
        "#let fenced = ```\n"
        "Literal \\$ in multiline fence stays verbatim\n"
        "```\n"
        "#text[Valid content escape \\$100 and *bold*]\n"
    )
    assert mod.scan_typst_escaping_issues(source, label="deck.typ") == []


@pytest.mark.parametrize(
    ("snippet", "expected"),
    [
        ('#let v = "Cost \\$10"\n', "unexpected '\\$' inside string literal"),
        ('#let v = "Around \\~5%"\n', "unexpected '\\~' inside string literal"),
        ('#let v = "Star \\*mark"\n', "unexpected '\\*' inside string literal"),
        ("#let v = `Cost \\$10`\n", "remove backslash in inline raw span"),
        ("#let v = `Rate \\~5`\n", "remove backslash in inline raw span"),
        ("#let v = `Wild \\*`\n", "remove backslash in inline raw span"),
    ],
)
def test_scan_typst_escaping_issues_rejects_bad_escapes(mod: ModuleType, snippet: str, expected: str) -> None:
    issues = mod.scan_typst_escaping_issues(snippet, label="deck.typ")
    assert len(issues) == 1
    assert expected in issues[0]


def test_discover_font_paths_finds_deck_repo_and_user_font_dirs(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    repo_fonts = repo / "assets" / "fonts"
    repo_fonts.mkdir(parents=True)

    deck_dir = repo / "talks" / "q4"
    deck_fonts = deck_dir / "fonts"
    deck_fonts.mkdir(parents=True)
    deck = deck_dir / "deck.typ"
    deck.write_text("#text[Hi]\n", encoding="utf-8")

    fake_home = tmp_path / "home"
    user_linux_fonts = fake_home / ".local" / "share" / "fonts"
    user_linux_fonts.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    extra = tmp_path / "custom-fonts"
    extra.mkdir()

    found = mod.discover_font_paths(deck, [extra, extra])
    assert found == [extra.resolve(), deck_fonts.resolve(), repo_fonts.resolve(), user_linux_fonts.resolve()]


def _install_fake_typst(
    mod: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    *,
    slides: int = 4,
    pdf_stderr: str = "",
    fail_on: str | None = None,
) -> list[list[str]]:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs: object) -> object:
        calls.append(command)
        target = command[-1]
        if fail_on and fail_on in target:
            return mod.subprocess.CompletedProcess(command, 1, "", "fatal typst syntax error")
        if "{p}.png" in target:
            pattern = Path(target)
            for idx in range(1, slides + 1):
                Path(str(pattern).replace("{p}", str(idx))).write_bytes(b"PNG")
            return mod.subprocess.CompletedProcess(command, 0, "", "")
        if target.endswith(".pdf"):
            Path(target).write_bytes(b"%PDF-1.7\n%mock\n")
            return mod.subprocess.CompletedProcess(command, 0, "", pdf_stderr)
        Path(target).write_text("<svg/>", encoding="utf-8")
        return mod.subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(mod.shutil, "which", lambda name: "/bin/typst" if name == "typst" else None)
    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    return calls


def test_check_cli_compiles_figures_pdf_and_pngs(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    deck_dir = tmp_path / "deck"
    figures_dir = deck_dir / "figures"
    preview_dir = deck_dir / "preview"
    figures_dir.mkdir(parents=True)
    deck = deck_dir / "deck.typ"
    deck.write_text("#text[Slide]\n", encoding="utf-8")
    (figures_dir / "chart.typ").write_text("#box[Chart]\n", encoding="utf-8")
    # Pre-seed stale slide beyond expected count to verify cleanup before compilation.
    preview_dir.mkdir()
    stale = preview_dir / "deck-99.png"
    stale.write_bytes(b"STALE")

    monkeypatch.setattr(Path, "home", lambda: tmp_path / "no-home")
    calls = _install_fake_typst(mod, monkeypatch, slides=4)

    rc = mod.main(
        [
            "check",
            str(deck),
            "--expected-slides",
            "4",
            "--png-dir",
            str(preview_dir),
            "--render-figures",
            "--json",
        ]
    )
    assert rc == 0
    assert not stale.exists()
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["slide_count"] == 4
    assert payload["rendered_figures"] == [str(figures_dir / "chart.svg")]
    assert len(calls) == 3  # 1 figure + 1 PDF + 1 PNG set


def test_check_cli_rejects_overflow_font_warning_star_warning_and_bad_escapes(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "no-home")
    deck = tmp_path / "deck.typ"
    deck.write_text('#let s = "Bad \\$"\n', encoding="utf-8")

    # 1. Static escaping scanner fails before calling typst.
    assert mod.main(["check", str(deck), "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["ok"] is False

    # 2. Slide count mismatch fails overflow gate.
    deck.write_text("#text[Clean]\n", encoding="utf-8")
    _install_fake_typst(mod, monkeypatch, slides=5)
    assert mod.main(["check", str(deck), "--expected-slides", "4", "--json"]) == 1
    captured = capsys.readouterr()
    assert json.loads(captured.out)["ok"] is False
    assert "Overflow/mismatch" in captured.err

    # 3. `no text within stars` warning fails.
    _install_fake_typst(mod, monkeypatch, slides=4, pdf_stderr="warning: no text within stars\n")
    assert mod.main(["check", str(deck), "--expected-slides", "4"]) == 1
    assert "empty bold stars" in capsys.readouterr().err

    # 4. `unknown font family` fails strictly, but succeeds when `--allow-font-warnings` is explicit.
    _install_fake_typst(mod, monkeypatch, slides=4, pdf_stderr="warning: unknown font family: google sans\n")
    assert mod.main(["check", str(deck), "--expected-slides", "4"]) == 1
    assert "unknown font family" in capsys.readouterr().err

    assert mod.main(["check", str(deck), "--expected-slides", "4", "--allow-font-warnings", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True


def test_check_cli_validates_arguments(mod: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "missing.typ"
    assert mod.main(["check", str(missing)]) == 1
    assert "existing .typ file" in capsys.readouterr().err

    wrong_ext = tmp_path / "notes.md"
    wrong_ext.write_text("# Notes\n", encoding="utf-8")
    assert mod.main(["check", str(wrong_ext)]) == 1
    assert "existing .typ file" in capsys.readouterr().err


def test_upload_cli_validates_pdf_and_dry_run(
    mod: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    not_pdf = tmp_path / "fake.pdf"
    not_pdf.write_bytes(b"not a pdf")
    assert mod.main(["upload", str(not_pdf), "--drive-folder", "folder_123"]) == 1
    assert "%PDF- header" in capsys.readouterr().err

    valid_pdf = tmp_path / "deck.pdf"
    valid_pdf.write_bytes(b"%PDF-1.7\nbody\n")
    assert mod.main(["upload", str(valid_pdf)]) == 1
    assert "Specify --file-id" in capsys.readouterr().err

    assert mod.main(["upload", str(valid_pdf), "--drive-folder", "bad/id"]) == 1
    assert "Invalid Google Drive folder ID" in capsys.readouterr().err

    assert mod.main(["upload", str(valid_pdf), "--drive-folder", "folder_123", "--name", "a/b.pdf"]) == 1
    assert "plain filename" in capsys.readouterr().err

    assert (
        mod.main(
            [
                "upload",
                str(valid_pdf),
                "--drive-folder",
                "folder_123",
                "--protect-copy",
                "--dry-run",
                "--json",
            ]
        )
        == 0
    )
    dry = json.loads(capsys.readouterr().out)
    assert dry["dry_run"] is True
    assert dry["protect_copy"] is True
    assert dry["local_size"] == len(b"%PDF-1.7\nbody\n")


def test_upload_cli_paginates_stages_in_private_dir_and_verifies_md5(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pdf_bytes = b"%PDF-1.7\nactual deck bytes\n"
    pdf_path = tmp_path / "q4-deck.pdf"
    pdf_path.write_bytes(pdf_bytes)
    expected_md5 = hashlib.md5(pdf_bytes, usedforsecurity=False).hexdigest()
    expected_size = len(pdf_bytes)

    calls: list[list[str]] = []
    cwds: list[Path] = []
    list_pages = 0

    def fake_run(command: list[str], *, cwd: str | None = None, **_kwargs: object) -> object:
        nonlocal list_pages
        assert cwd is not None
        cwd_path = Path(cwd)
        cwds.append(cwd_path)
        calls.append(command)
        verb = command[1:4]  # ["drive", "files", "<verb>"]
        if verb == ["drive", "files", "list"]:
            list_pages += 1
            if list_pages == 1:
                body: dict[str, object] = {"files": [], "nextPageToken": "page-2"}
            else:
                body = {"files": [{"id": "existing_file_99", "name": "q4-deck.pdf"}]}
            return mod.subprocess.CompletedProcess(command, 0, json.dumps(body), "")
        if verb == ["drive", "files", "update"]:
            staged = cwd_path / "q4-deck.pdf"
            assert staged.is_file()
            return mod.subprocess.CompletedProcess(command, 0, json.dumps({"id": "existing_file_99"}), "")
        if verb == ["drive", "files", "create"]:
            return mod.subprocess.CompletedProcess(command, 0, json.dumps({"id": "created_file_1"}), "")
        if verb == ["drive", "files", "get"]:
            return mod.subprocess.CompletedProcess(
                command,
                0,
                json.dumps(
                    {
                        "id": "existing_file_99",
                        "name": "q4-deck.pdf",
                        "webViewLink": "https://drive.google.com/file/d/existing_file_99/view",
                        "md5Checksum": expected_md5,
                        "size": str(expected_size),
                        "copyRequiresWriterPermission": True,
                    }
                ),
                "",
            )
        msg = f"Unexpected gws command: {command}"
        raise AssertionError(msg)

    monkeypatch.setattr(mod.shutil, "which", lambda name: "/bin/gws" if name == "gws" else None)
    monkeypatch.setattr(mod.subprocess, "run", fake_run)

    rc = mod.main(
        [
            "upload",
            str(pdf_path),
            "--drive-folder",
            "folder_abc123",
            "--protect-copy",
            "--json",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["operation"] == "updated"
    assert payload["file_id"] == "existing_file_99"
    assert payload["md5Checksum"] == expected_md5
    assert list_pages == 2
    assert len(set(cwds)) == 1
    assert not cwds[0].resolve().is_relative_to(tmp_path.resolve())
    assert not cwds[0].exists()

    # Updating via --file-id without --name creates no rename payload, and MD5 mismatch fails closed.
    calls.clear()
    assert mod.main(["upload", str(pdf_path), "--file-id", "direct_id_77", "--json"]) == 0
    assert "--json" not in calls[0]  # no metadata patch when neither --name nor --protect-copy is set
    capsys.readouterr()

    # Corrupt checksum from remote fails integrity gate.
    monkeypatch.setattr(
        mod,
        "_run_gws",
        lambda _args, **_kw: {"id": "direct_id_77", "md5Checksum": "0000", "size": expected_size},
    )
    assert mod.main(["upload", str(pdf_path), "--file-id", "direct_id_77", "--json"]) == 1
    assert "Integrity mismatch" in capsys.readouterr().err
