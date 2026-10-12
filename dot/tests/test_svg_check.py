"""Exercise the SVG illustration checker against the template and broken variants."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

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


def test_render_writes_brand_and_fallback_screenshots(
    svg: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    browser = tmp_path / "chrome"
    browser.write_text(
        f"#!{sys.executable}\n"
        "import sys\nfrom pathlib import Path\n"
        "args=sys.argv[1:]\n"
        "shot=next(a.split('=',1)[1] for a in args if a.startswith('--screenshot='))\n"
        "source=Path(args[-1].removeprefix('file://')).read_text()\n"
        "Path(shot).write_text(source)\n"
    )
    browser.chmod(0o700)
    monkeypatch.setenv("CHROME", str(browser))
    out = tmp_path / "shots"
    assert svg.main([str(TEMPLATE), "--render", str(out)]) == 0
    assert "Google Sans" in (out / "illustration.png").read_text()
    assert "Google Sans" not in (out / "illustration.fallback.png").read_text()
    assert not (out / "illustration.fallback.svg").exists()
    assert "rendered" in capsys.readouterr().out


def test_missing_file_fails(svg: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert svg.main([str(tmp_path / "absent.svg")]) == 1
    assert "file not found" in capsys.readouterr().out
