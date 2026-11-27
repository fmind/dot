"""Exercise the Typst 16:9 slide deck compiler, PPTX builder, and warning gates."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

from repo_helpers import ROOT, load_script, native_binary

SCRIPT = ROOT / "skills/draft/references/typst-deck/scripts/build_typst_deck.py"
TEMPLATE_DECK = ROOT / "skills/draft/references/typst-deck/templates/deck.typ"


@pytest.fixture
def mod() -> ModuleType:
    return load_script("build_typst_deck", SCRIPT)


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
            return subprocess.CompletedProcess(command, 1, "", "fatal typst syntax error")
        if "{p}.png" in target:
            pattern = Path(target)
            for idx in range(1, slides + 1):
                Path(str(pattern).replace("{p}", str(idx))).write_bytes(b"PNG")
            return subprocess.CompletedProcess(command, 0, "", "")
        if target.endswith(".pdf"):
            Path(target).write_bytes(b"%PDF-1.7\n%mock\n")
            return subprocess.CompletedProcess(command, 0, "", pdf_stderr)
        Path(target).write_text("<svg/>", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(shutil, "which", lambda name: "/bin/typst" if name == "typst" else None)
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


def test_check_cli_rejects_overflow_font_warning_and_star_warning(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "no-home")
    deck = tmp_path / "deck.typ"
    deck.write_text("#text[Clean]\n", encoding="utf-8")

    # 1. Slide count mismatch fails overflow gate.
    _install_fake_typst(mod, monkeypatch, slides=5)
    assert mod.main(["check", str(deck), "--expected-slides", "4", "--json"]) == 1
    captured = capsys.readouterr()
    assert json.loads(captured.out)["ok"] is False
    assert "Overflow/mismatch" in captured.err

    # 2. `no text within stars` warning fails.
    _install_fake_typst(mod, monkeypatch, slides=4, pdf_stderr="warning: no text within stars\n")
    assert mod.main(["check", str(deck), "--expected-slides", "4"]) == 1
    assert "empty bold stars" in capsys.readouterr().err

    # 3. `unknown font family` fails strictly, but succeeds when `--allow-font-warnings` is explicit.
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
    built = mod.pptx_builder.build_pptx(
        slides,
        out_pptx,
        title="Executive Review",
        speaker_notes={1: "Open with CTA.", 2: "Line 1 & <tag>\nLine 2"},
    )
    assert built == out_pptx
    original_bytes = out_pptx.read_bytes()

    with pytest.raises(FileNotFoundError):
        mod.pptx_builder.build_pptx([slides[0], tmp_path / "missing.png"], out_pptx, title="Broken")
    assert out_pptx.read_bytes() == original_bytes
    assert list(out_pptx.parent.glob("*.tmp")) == []

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
        if os.environ.get("CI"):
            pytest.fail("typst CLI must be installed in CI via mise.toml")
        pytest.skip("typst CLI unavailable")
    monkeypatch.setenv("PATH", f"{typst_bin.parent}{os.pathsep}{os.environ.get('PATH', '')}")

    deck_dir = tmp_path / "deck"
    deck_dir.mkdir()
    for name in ("fmind.typ", "fmind-slides.typ", "deck.typ"):
        (deck_dir / name).write_text((TEMPLATE_DECK.parent / name).read_text(encoding="utf-8"), encoding="utf-8")
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
    with zipfile.ZipFile(pptx_path, "r") as zf:
        slide_names = [n for n in zf.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")]
        assert len(slide_names) == 4
        assert "Q4 Compute Vendor Proposal" in zf.read("docProps/core.xml").decode("utf-8")


def test_render_cli_compiles_figure_card_and_fails_on_warnings(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    typst_bin = native_binary("typst")
    if typst_bin is None:
        if os.environ.get("CI"):
            pytest.fail("typst CLI must be installed in CI via mise.toml")
        pytest.skip("typst CLI unavailable")
    monkeypatch.setenv("PATH", f"{typst_bin.parent}{os.pathsep}{os.environ.get('PATH', '')}")

    card_dir = tmp_path / "card"
    card_dir.mkdir()
    for name in ("fmind.typ", "fmind-slides.typ", "figure-card.typ"):
        (card_dir / name).write_text((TEMPLATE_DECK.parent / name).read_text(encoding="utf-8"), encoding="utf-8")

    rc = mod.main(["render", str(card_dir / "figure-card.typ"), "--allow-font-warnings", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    out_png = Path(payload["output"])
    assert out_png.is_file()
    assert out_png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

    def fake_warn_typst(args: list[str]) -> object:
        if args and args[0] == "compile":
            target = Path(args[-1].replace("{p}", "1"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"\x89PNG\r\n\x1a\nimg")
            return subprocess.CompletedProcess(args, 0, "", "warning: unknown font family: google sans\n")
        return subprocess.CompletedProcess(args, 0, "{}", "")

    monkeypatch.setattr(mod, "run_typst", fake_warn_typst)
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
        if os.environ.get("CI"):
            pytest.fail("typst CLI must be installed in CI via mise.toml")
        pytest.skip("typst CLI unavailable")
    monkeypatch.setenv("PATH", f"{typst_bin.parent}{os.pathsep}{os.environ.get('PATH', '')}")

    deck_dir = tmp_path / "crowded"
    deck_dir.mkdir()
    for name in ("fmind.typ", "fmind-slides.typ"):
        (deck_dir / name).write_text((TEMPLATE_DECK.parent / name).read_text(encoding="utf-8"), encoding="utf-8")
    words = " ".join(f"word{i}" for i in range(40))
    (deck_dir / "deck.typ").write_text(
        f'#import "fmind-slides.typ": *\n#show: fmind-deck.with(title: "Test")\n#slide(title: "Too dense")[{words}]\n',
        encoding="utf-8",
    )
    assert mod.main(["check", str(deck_dir / "deck.typ"), "--max-words", "30", "--allow-font-warnings"]) == 1
    assert "Slide word limit exceeded" in capsys.readouterr().err

    # Closing appendix slides (`appendix: true`) are counted and reported without tripping `--max-words`.
    (deck_dir / "with_appendix.typ").write_text(
        '#import "fmind-slides.typ": *\n'
        '#show: fmind-deck.with(title: "Test")\n'
        '#slide(title: "Main")[Short visual anchor.]\n'
        f'#slide(title: "Annex", appendix: true)[{words}]\n',
        encoding="utf-8",
    )
    assert (
        mod.main(["check", str(deck_dir / "with_appendix.typ"), "--max-words", "30", "--allow-font-warnings", "--json"])
        == 0
    )
    appendix_payload = json.loads(capsys.readouterr().out)
    assert appendix_payload["ok"] is True
    assert appendix_payload["appendix_slides"] == [2]
    assert appendix_payload["slide_words"]["2"] > 30
    assert appendix_payload["word_violations"] == {}


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
                return subprocess.CompletedProcess(args, 0, "", "warning: layout did not converge within 5 attempts\n")
            target.write_bytes(b"%PDF-1.7\n")
            return subprocess.CompletedProcess(args, 0, "", "warning: unknown font family: google sans\n")
        return subprocess.CompletedProcess(args, 0, "{}", "")

    monkeypatch.setattr(mod, "run_typst", fake_png_warning_typst)
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


def test_failed_check_gates_preserve_existing_pptx_and_literal_auto_name(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "no-home")
    deck = tmp_path / "deck.typ"
    deck.write_text("#text[Slide]\n", encoding="utf-8")
    existing_pptx = tmp_path / "deck.pptx"
    existing_pptx.write_bytes(b"KEEP-EXISTING-PPTX")

    def fake_run(command: list[str], **_kwargs: object) -> object:
        if command[1] == "eval":
            payload = {"notes": [], "meta": [{"title": "Deck"}], "words": [{"page": 1, "words": 50}]}
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        target = command[-1]
        if "{p}.png" in target:
            Path(target.replace("{p}", "1")).write_bytes(b"\x89PNG\r\n\x1a\nimg")
            return subprocess.CompletedProcess(command, 0, "", "")
        Path(target).write_bytes(b"%PDF-1.7\n")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(shutil, "which", lambda name: "/bin/typst" if name == "typst" else None)
    monkeypatch.setattr(mod.subprocess, "run", fake_run)

    # Overflow and word-cap failures must never clobber existing .pptx.
    assert mod.main(["check", str(deck), "--pptx", "--expected-slides", "2", "--json"]) == 1
    assert existing_pptx.read_bytes() == b"KEEP-EXISTING-PPTX"
    assert "pptx" not in json.loads(capsys.readouterr().out)

    assert mod.main(["check", str(deck), "--pptx", "--max-words", "30", "--json"]) == 1
    assert existing_pptx.read_bytes() == b"KEEP-EXISTING-PPTX"
    assert "pptx" not in json.loads(capsys.readouterr().out)

    # Explicit `--pptx __AUTO__` resolves to a literal file path instead of triggering the default sentinel.
    monkeypatch.chdir(tmp_path)
    assert mod.main(["check", str(deck), "--pptx", "__AUTO__", "--expected-slides", "1", "--json"]) == 0
    out_payload = json.loads(capsys.readouterr().out)
    assert Path(out_payload["pptx"]) == (tmp_path / "__AUTO__").resolve()
    assert (tmp_path / "__AUTO__").is_file()
    assert (Path(out_payload["pptx"]).stat().st_mode & 0o777) == 0o600


def test_fmind_typ_template_matches_pinned_theme_checksum(tmp_path: Path) -> None:
    import hashlib
    import tomllib

    from repo_helpers import chezmoi

    template = (ROOT / ".chezmoiexternal.toml.tmpl").read_text(encoding="utf-8")
    rendered = tomllib.loads(chezmoi(tmp_path, "execute-template", stdin=template))
    expected_sha = rendered[".agents/themes/typst/fmind.typ"]["checksum"]["sha256"]
    bundled = ROOT / "skills/draft/references/typst-deck/templates/fmind.typ"
    actual_sha = hashlib.sha256(bundled.read_bytes()).hexdigest()
    assert actual_sha == expected_sha, "skills/draft/.../templates/fmind.typ drifted from .chezmoiexternal.toml.tmpl"


def test_render_figures_fails_closed_when_figures_empty(
    mod: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    deck = tmp_path / "deck.typ"
    deck.write_text("#text[Slide]\n", encoding="utf-8")
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "no-home")
    _install_fake_typst(mod, monkeypatch, slides=1)
    assert mod.main(["check", str(deck), "--expected-slides", "1", "--render-figures", "--json"]) == 1
    err = capsys.readouterr().err
    assert "no .typ files" in err.lower() or "figures" in err.lower()


def test_fmind_slides_word_count_handles_callout_terms_and_unicode(tmp_path: Path) -> None:
    typst = native_binary("typst")
    if typst is None:
        pytest.skip("typst not installed")
    tpl_dir = ROOT / "skills/draft/references/typst-deck/templates"
    for name in ("fmind.typ", "fmind-slides.typ"):
        shutil.copy2(tpl_dir / name, tmp_path / name)
    probe = tmp_path / "probe.typ"
    probe.write_text(
        '#import "fmind-slides.typ": *\n'
        '#show: fmind-deck.with(title: "Test", context-label: "Eng", date: "2026")\n'
        '#slide(title: "Probe")[\n'
        '  #callout(title: "Note")[three more words]\n'
        "  / Key: value word\n"
        "  à à à\n"
        "]\n",
        encoding="utf-8",
    )
    res = subprocess.run(
        [str(typst), "eval", "--root", str(tmp_path), "--in", str(probe), "query(<fmind-slide-words>)"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert res.returncode == 0, res.stderr
    entries = json.loads(res.stdout)
    # "Probe" (1) + "Note" (1) + "three more words" (3) + "Key" (1) + "value word" (2) + "à à à" (3) = 11 words
    assert entries[0]["value"]["words"] == 11
