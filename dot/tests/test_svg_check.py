"""Exercise the SVG illustration checker against the template and broken variants."""

import base64
import importlib.util
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from types import ModuleType
from urllib.parse import unquote, urlsplit

import pytest

GUIDE = Path(__file__).resolve().parents[2] / "skills/diagrams-as-code/references/svg"
SCRIPT = GUIDE / "scripts/check_svg.py"
TEMPLATE = GUIDE / "templates/illustration.svg"


@pytest.fixture
def svg() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_svg", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def symlinked_tmp_path(tmp_path: Path) -> Path:
    """Mirror macOS /var -> /private/var even on Linux."""
    real = tmp_path / "private" / "var" / "folders"
    real.mkdir(parents=True)
    alias = tmp_path / "var"
    alias.symlink_to(real.parent, target_is_directory=True)
    return alias / "folders"


def variant(tmp_path: Path, old: str, new: str) -> Path:
    text = TEMPLATE.read_text(encoding="utf-8")
    assert old in text
    path = tmp_path / "concept.svg"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return path


def test_template_passes(svg: ModuleType) -> None:
    assert svg.check(TEMPLATE, 960) == []


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        ('role="img" ', "", 'role="img"'),
        ('<desc id="desc">', '<desc id="other">', "missing id 'desc'"),
        ('aria-labelledby="title desc"', 'aria-labelledby="card"', "<title> needs an id referenced"),
        ('<desc id="desc">', "<desc>", "<desc> needs an id referenced"),
        ("font-size: 12px;", "font-size: 10px;", "font-size 10px"),
        ("font-size: 12px;", "font-size: 1.2.3px;", "invalid font-size"),
        ("</defs>", '</defs><image href="https://example.com/a.png"/>', "external or raster"),
        ("</defs>", "</defs><script>alert(1)</script>", "<script>"),
        ("<style>\ntext", '<style>@import url("https://fonts.example/x.css");\ntext', "imports"),
        ('viewBox="0 0 960 420"', 'viewBox="0 0 800 420"', "expected 960"),
        ("</svg>", "", "well-formed"),
    ],
)
def test_guide_violations_are_reported(svg: ModuleType, tmp_path: Path, old: str, new: str, expected: str) -> None:
    problems = svg.check(variant(tmp_path, old, new), 960)
    assert any(expected in problem for problem in problems), problems


@pytest.mark.parametrize(
    "viewbox",
    ["0 0 960 NaN", "0 0 960 inf", "0 0 960 0", "0 0 960 -1", "inf 0 960 420", "text 0 960 420"],
)
def test_invalid_geometry_fails_before_rendering(
    svg: ModuleType, tmp_path: Path, viewbox: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    path = variant(tmp_path, 'viewBox="0 0 960 420"', f'viewBox="{viewbox}"')

    def unexpected_render(*_args: object) -> None:
        pytest.fail("invalid geometry must not launch a browser")

    monkeypatch.setattr(svg, "render", unexpected_render)
    assert svg.main([str(path), "--render", str(tmp_path / "shots")]) == 1
    assert "invalid viewBox" in capsys.readouterr().out


def test_accessible_label_must_reference_the_title_and_description(svg: ModuleType, tmp_path: Path) -> None:
    path = variant(tmp_path, 'aria-labelledby="title desc"', 'aria-labelledby="unrelated"')
    path.write_text(path.read_text().replace("</svg>", '<text id="unrelated">Other text</text></svg>'))

    problems = svg.check(path, 960)

    assert any("<title> needs an id referenced" in problem for problem in problems)
    assert any("<desc> needs an id referenced" in problem for problem in problems)


def test_title_and_description_cannot_share_an_id(svg: ModuleType, tmp_path: Path) -> None:
    path = variant(tmp_path, '<desc id="desc">', '<desc id="title">')
    path.write_text(path.read_text().replace('aria-labelledby="title desc"', 'aria-labelledby="title"'))

    assert "duplicate id 'title'" in svg.check(path, 960)


def test_render_embeds_brand_and_fallback_bytes_with_symlinked_paths(
    svg: ModuleType, symlinked_tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Neither path aliases nor special characters may become file subresources.
    source = symlinked_tmp_path / 'a "quoted" & <special> #é.svg'
    source.write_bytes(TEMPLATE.read_bytes())
    monkeypatch.setattr(svg.tempfile, "tempdir", str(symlinked_tmp_path))
    temporary_files: list[Path] = []

    def screenshot(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
        wrapper = Path(unquote(urlsplit(command[-1]).path))
        assert wrapper.suffix == ".html"
        assert wrapper == wrapper.resolve()
        document = ET.fromstring(wrapper.read_text())  # noqa: S314 - generated local HTML fixture
        assert [element.tag for element in document.iter()] == ["html", "head", "meta", "style", "body", "img"]
        img = document.find("body/img")
        assert img is not None
        prefix, encoded = img.attrib["src"].split(",", 1)
        assert prefix == "data:image/svg+xml;base64"
        content = base64.b64decode(encoded, validate=True)
        temporary_files.append(wrapper)
        if len(temporary_files) == 1:
            assert content == source.read_bytes()
        else:
            assert content == svg.BRAND_FONTS.sub("", source.read_text(encoding="utf-8")).encode("utf-8")
        shot = Path(next(arg.split("=", 1)[1] for arg in command if arg.startswith("--screenshot=")))
        shot.write_bytes(content)
        return subprocess.CompletedProcess(command, 0, b"", b"")

    monkeypatch.setattr(svg, "chrome", lambda: "chrome")
    monkeypatch.setattr(svg.subprocess, "run", screenshot)
    out = symlinked_tmp_path.resolve() / "shots"
    out.mkdir()
    existing = out / f"{source.stem}.fallback.svg"
    existing.write_text("preserve an existing file")
    assert svg.main([str(source), "--render", str(out)]) == 0
    assert "Google Sans" in (out / f"{source.stem}.png").read_text()
    assert "Google Sans" not in (out / f"{source.stem}.fallback.png").read_text()
    assert existing.read_text() == "preserve an existing file"
    assert all(not path.exists() for path in temporary_files)
    assert "rendered" in capsys.readouterr().out


@pytest.mark.parametrize("timed_out", [False, True])
def test_render_cleans_temporary_files_on_browser_failure(
    svg: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    timed_out: bool,
) -> None:
    wrappers: list[Path] = []

    def fail(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
        wrappers.append(Path(unquote(urlsplit(command[-1]).path)))
        if timed_out:
            raise subprocess.TimeoutExpired(command, 60)
        return subprocess.CompletedProcess(command, 1, b"", b"browser failed")

    monkeypatch.setattr(svg, "chrome", lambda: "chrome")
    monkeypatch.setattr(svg.subprocess, "run", fail)
    out = tmp_path / "shots"
    assert svg.main([str(TEMPLATE), "--render", str(out)]) == 1
    assert ("timed out" if timed_out else "browser failed") in capsys.readouterr().err
    assert wrappers
    assert all(not path.parent.exists() for path in wrappers)
    assert list(out.iterdir()) == []


def test_browser_keeps_svg_events_inert_and_clean_pixels_unchanged(
    svg: ModuleType, symlinked_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    try:
        binary = svg.chrome()
    except RuntimeError:
        pytest.skip("Chrome/Chromium is required for the SVG image-context regression")

    # Temp wrappers start below /var, while the inputs and shots use /private/var.
    monkeypatch.setattr(svg.tempfile, "tempdir", str(symlinked_tmp_path))
    source_dir = symlinked_tmp_path.resolve()
    clean = source_dir / "clean.svg"
    clean.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
    event = source_dir / "event.svg"
    event.write_text(
        clean.read_text().replace("<svg ", "<svg onload=\"document.querySelector('rect').style.fill='magenta'\" ", 1),
        encoding="utf-8",
    )
    # This deliberately passes the authoring checks: image isolation must hold
    # independently of the static checker's coverage of executable SVG features.
    assert svg.check(event, 960) == []
    out = source_dir / "shots"
    out.mkdir()
    assert svg.main([str(clean), str(event), "--render", str(out)]) == 0

    def direct(source: Path, name: str) -> bytes:
        shot = out / name
        result = subprocess.run(
            [
                binary,
                "--headless=new",
                "--hide-scrollbars",
                "--disable-gpu",
                f"--user-data-dir={source_dir / 'control-profile'}",
                "--window-size=960,420",
                f"--screenshot={shot}",
                source.as_uri(),
            ],
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=60,
            check=False,
        )
        assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
        return shot.read_bytes()

    # Positive control: opening the synthetic SVG as a document executes onload.
    original = direct(clean, "direct.png")
    assert direct(event, "active.png") != original
    assert (out / "clean.png").read_bytes() == original
    assert (out / "event.png").read_bytes() == original
    fallback = source_dir / "fallback.svg"
    fallback.write_text(svg.BRAND_FONTS.sub("", clean.read_text()), encoding="utf-8")
    original_fallback = direct(fallback, "direct-fallback.png")
    assert (out / "clean.fallback.png").read_bytes() == original_fallback
    assert (out / "event.fallback.png").read_bytes() == original_fallback


def test_missing_file_fails(svg: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert svg.main([str(tmp_path / "absent.svg")]) == 1
    assert "file not found" in capsys.readouterr().out
