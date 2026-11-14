"""Exercise the Typst 16:9 slide deck compiler and safe Google Drive uploader."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

from tests.fakes import native_binary

SCRIPT = Path(__file__).resolve().parents[2] / "skills/draft-typst-deck/scripts/build_typst_deck.py"
TEMPLATE_DECK = Path(__file__).resolve().parents[2] / "skills/draft-typst-deck/templates/deck.typ"
EDITABLE_TEMPLATE = Path(__file__).resolve().parents[2] / "skills/draft-typst-deck/templates/editable_deck.py"


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
        'Prose quotes "around \\$100 and [nested]" stay valid in markup mode.\n'
        '#slide(title: "Clean $10")[He said "save \\$10 and \\~5%" in content mode.]\n'
        '#heading[Quoted "asterisks \\*" in markup]\n'
        '#[Explicit content block with "quoted \\$100" stays markup]\n'
        '#box[#let x = "clean $10"] "Prose quote \\$10 after inline #let stays markup"\n'
        '#let pair = (#let inner = "clean $5"; inner)\n'
    )
    assert mod.scan_typst_escaping_issues(source, label="deck.typ") == []


@pytest.mark.parametrize(
    ("snippet", "expected"),
    [
        ('#let v = "Cost \\$10"\n', "unexpected '\\$' inside string literal"),
        ('#let v = "Around \\~5%"\n', "unexpected '\\~' inside string literal"),
        ('#let v = "Star \\*mark"\n', "unexpected '\\*' inside string literal"),
        ('#slide(title: "Cost \\$10")[Body]\n', "unexpected '\\$' inside string literal"),
        ('#"Cost \\$10"\n', "unexpected '\\$' inside string literal"),
        ('#box[#let v = "Cost \\$10"]\n', "unexpected '\\$' inside string literal"),
        ('#[#("Cost \\$10")]\n', "unexpected '\\$' inside string literal"),
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
    unrelated = preview_dir / "deck-backup-1.png"
    unrelated.write_bytes(b"KEEP")

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
    assert unrelated.is_file()
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

    assert mod.main(["upload", str(valid_pdf), "--drive-folder", "folder_123", "--name=-flag.pdf"]) == 1
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


def test_check_cli_rejects_output_overwriting_typst_source(
    mod: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    deck = tmp_path / "deck.typ"
    deck.write_text("#text[Keep deck source intact]\n", encoding="utf-8")
    theme = tmp_path / "fmind-slides.typ"
    theme.write_text("// theme\n", encoding="utf-8")

    for bad_out in (deck, theme, tmp_path / "other.typ"):
        assert mod.main(["check", str(deck), "-o", str(bad_out)]) == 1
        assert "Output PDF path must differ from Typst source files" in capsys.readouterr().err
    assert deck.read_text(encoding="utf-8") == "#text[Keep deck source intact]\n"
    assert theme.read_text(encoding="utf-8") == "// theme\n"


def test_build_pptx_packages_16x9_slides_and_speaker_notes(mod: ModuleType, tmp_path: Path) -> None:
    slides = []
    for idx in range(1, 3):
        img = tmp_path / f"s-{idx}.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + f"slide-{idx}".encode())
        slides.append(img)

    out_pptx = tmp_path / "out" / "review.pptx"
    built = mod.build_pptx(
        slides,
        out_pptx,
        title="Executive Review",
        speaker_notes={1: "Open with CTA.", 2: "Line 1 & <tag>\nLine 2"},
    )
    assert built == out_pptx
    assert mod.inspect_pptx_metadata(out_pptx)[0] == 2

    with zipfile.ZipFile(out_pptx, "r") as zf:
        names = set(zf.namelist())
        assert {
            "[Content_Types].xml",
            "ppt/presentation.xml",
            "ppt/slides/slide1.xml",
            "ppt/slides/slide2.xml",
            "ppt/media/slide-01.png",
            "ppt/media/slide-02.png",
            "ppt/notesSlides/notesSlide1.xml",
            "ppt/notesSlides/notesSlide2.xml",
        } <= names
        pres_xml = zf.read("ppt/presentation.xml").decode()
        assert '<p:sldSz cx="9144000" cy="5143500" type="screen16x9"/>' in pres_xml
        notes2 = zf.read("ppt/notesSlides/notesSlide2.xml").decode()
        assert "Line 1 &amp; &lt;tag&gt;" in notes2
        assert "Line 2" in notes2


def test_check_cli_compiles_template_deck_to_pptx_and_extracts_notes(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    typst_bin = native_binary("typst")
    if typst_bin is None:
        pytest.skip("typst CLI unavailable")
    monkeypatch.setenv("PATH", f"{typst_bin.parent}{os.pathsep}{os.environ.get('PATH', '')}")

    deck_dir = tmp_path / "deck"
    deck_dir.mkdir()
    for name in ("fmind-slides.typ", "deck.typ"):
        (deck_dir / name).write_text((TEMPLATE_DECK.parent / name).read_text(encoding="utf-8"), encoding="utf-8")
    # Ensure check doesn't fail on a headless host lacking preinstalled Google Sans fonts.
    rc = mod.main(
        [
            "check",
            str(deck_dir / "deck.typ"),
            "--expected-slides",
            "4",
            "--max-words",
            "30",
            "--pptx",
            "--allow-font-warnings",
            "--json",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["slide_count"] == 4
    assert payload["speaker_notes_slides"] == [1, 2, 3, 4]
    assert set(payload["slide_words"]) == {"1", "2", "3", "4"}
    assert all(count <= 30 for count in payload["slide_words"].values())
    pptx_path = Path(payload["pptx"])
    assert pptx_path.is_file()
    assert mod.inspect_pptx_metadata(pptx_path) == (4, "Q4 Compute Vendor Proposal")


def test_upload_cli_converts_pptx_to_google_slides_and_syncs_sources(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    src_dir = tmp_path / "deck"
    src_dir.mkdir()
    (src_dir / "deck.typ").write_text("#text[Slide]\n", encoding="utf-8")
    png = tmp_path / "slide-1.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\nimg")
    pptx = mod.build_pptx([png], src_dir / "deck.pptx", title="Deck", speaker_notes={1: "Note 1"})

    pdf = tmp_path / "deck.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    assert mod.main(["upload", str(pdf), "--drive-folder", "folder_1", "--google-slides"]) == 1
    assert "--google-slides requires a .pptx" in capsys.readouterr().err

    def fake_gws(args: list[str], *, cwd: Path) -> dict[str, object]:
        prefix = tuple(args[:3])
        if prefix == ("drive", "files", "list"):
            return {"files": []}
        if prefix == ("drive", "files", "create"):
            body = json.loads(args[args.index("--json") + 1])
            mime = body["mimeType"]
            if mime == mod.FOLDER_MIME:
                return {"id": f"folder_{body['name']}"}
            if mime == mod.GOOGLE_SLIDES_MIME:
                staged = cwd / args[args.index("--upload") + 1]
                assert staged.is_file()
                return {"id": "slides_123"}
            staged_src = cwd / args[args.index("--upload") + 1]
            return {"id": f"src_{staged_src.name}"}
        if prefix == ("drive", "files", "get"):
            file_id = json.loads(args[args.index("--params") + 1])["fileId"]
            if file_id == "slides_123":
                return {
                    "id": "slides_123",
                    "name": "deck",
                    "mimeType": mod.GOOGLE_SLIDES_MIME,
                    "webViewLink": "https://docs.google.com/presentation/d/slides_123/edit",
                    "trashed": False,
                    "parents": ["folder_1"],
                }
            src_bytes = (src_dir / "deck.typ").read_bytes()
            src_md5 = hashlib.md5(src_bytes).hexdigest()  # noqa: S324
            return {"id": file_id, "md5Checksum": src_md5, "size": str(len(src_bytes))}
        if prefix == ("slides", "presentations", "get"):
            return {"presentationId": "slides_123", "title": "deck", "slides": [{"objectId": "p1"}]}
        msg = f"Unexpected gws args: {args}"
        raise AssertionError(msg)

    monkeypatch.setattr(mod, "_run_gws", fake_gws)
    rc = mod.main(
        [
            "upload",
            str(pptx),
            "--drive-folder",
            "folder_1",
            "--google-slides",
            "--source-dir",
            str(src_dir),
            "--json",
        ]
    )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["file_id"] == "slides_123"
    assert out["mimeType"] == mod.GOOGLE_SLIDES_MIME
    assert out["slide_count"] == 1
    assert out["synced_sources"] == [{"name": "deck.typ", "file_id": "src_deck.typ", "operation": "created"}]

    # Trashed or slide-count-mismatched Slides read-back fails closed.
    monkeypatch.setattr(
        mod,
        "_run_gws",
        lambda args, **_kw: (
            {"files": []}
            if args[:3] == ["drive", "files", "list"]
            else {"id": "slides_123"}
            if args[:3] == ["drive", "files", "create"]
            else {"id": "slides_123", "mimeType": mod.GOOGLE_SLIDES_MIME, "trashed": False}
            if args[:3] == ["drive", "files", "get"]
            else {"presentationId": "slides_123", "slides": []}
        ),
    )
    assert mod.main(["upload", str(pptx), "--drive-folder", "folder_1", "--google-slides"]) == 1
    assert "slide-count mismatch" in capsys.readouterr().err


def test_editable_deck_template_compiles_valid_python_syntax() -> None:
    source = EDITABLE_TEMPLATE.read_text(encoding="utf-8")
    assert "python-pptx==1.0.2" in source
    assert "kicker.upper()" not in source
    assert "_png_dimensions" in source
    assert "shape.text_frame" in source
    compile(source, str(EDITABLE_TEMPLATE), "exec")


def test_render_cli_compiles_figure_card_and_fails_on_warnings(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    typst_bin = native_binary("typst")
    if typst_bin is None:
        pytest.skip("typst CLI unavailable")
    monkeypatch.setenv("PATH", f"{typst_bin.parent}{os.pathsep}{os.environ.get('PATH', '')}")

    card_dir = tmp_path / "card"
    card_dir.mkdir()
    for name in ("fmind-slides.typ", "figure-card.typ"):
        (card_dir / name).write_text((TEMPLATE_DECK.parent / name).read_text(encoding="utf-8"), encoding="utf-8")

    rc = mod.main(["render", str(card_dir / "figure-card.typ"), "--allow-font-warnings", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    out_png = Path(payload["output"])
    assert out_png.is_file()
    assert out_png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

    # Simulated unknown font family warning fails closed on render and on check --render-figures.
    def fake_warn_typst(args: list[str]) -> object:
        if args and args[0] == "compile":
            target = Path(args[-1].replace("{p}", "1"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"\x89PNG\r\n\x1a\nimg")
            return mod.subprocess.CompletedProcess(args, 0, "", "warning: unknown font family: google sans\n")
        return mod.subprocess.CompletedProcess(args, 0, "{}", "")

    monkeypatch.setattr(mod, "_run_typst", fake_warn_typst)
    assert mod.main(["render", str(card_dir / "figure-card.typ"), "--json"]) == 1
    assert "unknown font family" in capsys.readouterr().err

    figures_dir = card_dir / "figures"
    figures_dir.mkdir()
    (figures_dir / "chart.typ").write_text("#text[Chart]\n", encoding="utf-8")
    (card_dir / "deck.typ").write_text(
        '#import "fmind-slides.typ": *\n#show: fmind-deck\n#slide[Hi]\n', encoding="utf-8"
    )
    assert mod.main(["check", str(card_dir / "deck.typ"), "--render-figures", "--figure-format", "png"]) == 1
    assert "unknown font family" in capsys.readouterr().err


def test_check_max_words_rejects_crowded_slide(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    typst_bin = native_binary("typst")
    if typst_bin is None:
        pytest.skip("typst CLI unavailable")
    monkeypatch.setenv("PATH", f"{typst_bin.parent}{os.pathsep}{os.environ.get('PATH', '')}")

    deck_dir = tmp_path / "crowded"
    deck_dir.mkdir()
    (deck_dir / "fmind-slides.typ").write_text(
        (TEMPLATE_DECK.parent / "fmind-slides.typ").read_text(encoding="utf-8"), encoding="utf-8"
    )
    words = " ".join(f"word{i}" for i in range(40))
    (deck_dir / "deck.typ").write_text(
        f'#import "fmind-slides.typ": *\n#show: fmind-deck.with(title: "Test")\n#slide(title: "Too dense")[{words}]\n',
        encoding="utf-8",
    )
    assert mod.main(["check", str(deck_dir / "deck.typ"), "--max-words", "30", "--allow-font-warnings"]) == 1
    assert "Slide word limit exceeded" in capsys.readouterr().err


def test_upload_uses_core_title_and_syncs_editable_python_sources(
    mod: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    src_dir = tmp_path / "pydeck"
    src_dir.mkdir()
    (src_dir / "editable_deck.py").write_text("print('deck')\n", encoding="utf-8")
    png = tmp_path / "s1.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\nimg")
    pptx = mod.build_pptx([png], src_dir / "editable-deck.pptx", title="Executive Review Q4")

    assert (
        mod.main(
            [
                "upload",
                str(pptx),
                "--drive-folder",
                "folder_9",
                "--google-slides",
                "--source-dir",
                str(src_dir),
                "--dry-run",
                "--json",
            ]
        )
        == 0
    )
    plan = json.loads(capsys.readouterr().out)
    assert plan["name"] == "Executive Review Q4"
    assert plan["source_files"] == ["editable_deck.py"]


def test_unexpected_typst_warnings_fail_even_with_allow_font_warnings(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    deck = tmp_path / "deck.typ"
    deck.write_text("#text[Clean]\n", encoding="utf-8")

    def fake_png_warning_typst(args: list[str]) -> object:
        if args and args[0] == "compile":
            target = Path(args[-1].replace("{p}", "1"))
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.suffix == ".png":
                target.write_bytes(b"\x89PNG\r\n\x1a\nimg")
                return mod.subprocess.CompletedProcess(
                    args, 0, "", "warning: layout did not converge within 5 attempts\n"
                )
            target.write_bytes(b"%PDF-1.7\n")
            return mod.subprocess.CompletedProcess(args, 0, "", "warning: unknown font family: google sans\n")
        return mod.subprocess.CompletedProcess(args, 0, "{}", "")

    monkeypatch.setattr(mod, "_run_typst", fake_png_warning_typst)
    assert mod.main(["render", str(deck), "--allow-font-warnings", "--json"]) == 1
    render_err = capsys.readouterr()
    assert json.loads(render_err.out)["ok"] is False
    assert "layout did not converge" in render_err.err

    assert mod.main(["check", str(deck), "--expected-slides", "1", "--allow-font-warnings", "--json"]) == 1
    check_err = capsys.readouterr()
    check_payload = json.loads(check_err.out)
    assert check_payload["ok"] is False
    assert len(check_payload["warnings"]) == 2
    assert "unexpected warnings" in check_err.err
