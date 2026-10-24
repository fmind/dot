"""Exercise the SVG illustration checker against the template and broken variants."""

import importlib.util
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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


@pytest.mark.parametrize("size", ["0.8em", "1.5rem", "120%", "10pt"])
def test_relative_font_sizes_are_not_read_as_pixels(svg: ModuleType, tmp_path: Path, size: str) -> None:
    assert svg.check(variant(tmp_path, "font-size: 12px;", f"font-size: {size};"), 960) == []


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


@pytest.mark.parametrize(
    ("markup", "expected"),
    [
        ('<g onload="void 0"/>', "event-handler attribute 'onload'"),
        ('<g onclick="void 0"/>', "event-handler attribute 'onclick'"),
        ('<g ONLOAD="void 0"/>', "event-handler attribute 'ONLOAD'"),
        ('<g xmlns:x="urn:test" x:onload="void 0"/>', "event-handler attribute 'onload'"),
        ('<a href="javascript:void(0)"/>', "javascript: URL"),
        ('<a href=" &#x09;JaVa&#x0A;ScRiPt:void(0)"/>', "javascript: URL"),
        ('<a href="j&#97;vascript:void(0)"/>', "javascript: URL"),
        (
            '<a xmlns:xlink="http://www.w3.org/1999/xlink" href="#card" xlink:href="javascript:void(0)"/>',
            "javascript: URL",
        ),
    ],
)
def test_executable_attributes_fail_before_rendering(
    svg: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    markup: str,
    expected: str,
) -> None:
    source = variant(tmp_path, "</svg>", markup + "</svg>")

    def unexpected_render(*_args: object) -> None:
        pytest.fail("executable attributes must not launch a browser")

    monkeypatch.setattr(svg, "render", unexpected_render)
    assert svg.main([str(source), "--render", str(tmp_path / "shots")]) == 1
    assert expected in capsys.readouterr().out


def test_render_writes_brand_and_fallback_screenshots(
    svg: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    browser = tmp_path / "chrome"
    browser.write_text(
        f"#!{sys.executable}\n"
        "import json, sys\nfrom pathlib import Path\n"
        "args=sys.argv[1:]\n"
        "assert '--host-resolver-rules=MAP * ^NOTFOUND' in args\n"
        "assert '--no-proxy-server' in args\n"
        "profile=Path(next(a.split('=',1)[1] for a in args if a.startswith('--user-data-dir=')))\n"
        "prefs=json.loads((profile/'Default'/'Preferences').read_text())\n"
        "assert prefs['profile']['default_content_setting_values']['javascript'] == 2\n"
        "assert args[-1].startswith('file://') and args[-1].endswith('.svg')\n"
        "shot=next(a.split('=',1)[1] for a in args if a.startswith('--screenshot='))\n"
        "source=Path(args[-1].removeprefix('file://')).read_text()\n"
        "Path(shot).write_text(source)\n"
    )
    browser.chmod(0o700)
    monkeypatch.setenv("CHROME", str(browser))
    out = tmp_path / "shots"
    out.mkdir()
    existing = out / "illustration.fallback.svg"
    existing.write_text("user-owned SVG")
    assert svg.main([str(TEMPLATE), "--render", str(out)]) == 0
    assert "Google Sans" in (out / "illustration.png").read_text()
    assert "Google Sans" not in (out / "illustration.fallback.png").read_text()
    assert existing.read_text() == "user-owned SVG"
    assert "rendered" in capsys.readouterr().out


@pytest.mark.parametrize("failure", ["no-output", "empty-output", "second-render", "timeout"])
def test_failed_render_preserves_sources_and_previous_screenshots(
    svg: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    source = tmp_path / "concept.svg"
    source.write_bytes(TEMPLATE.read_bytes())
    previous = {
        "concept.svg": source.read_bytes(),
        "concept.fallback.svg": b"user-owned source",
        "concept.png": b"previous brand screenshot",
        "concept.fallback.png": b"previous fallback screenshot",
    }
    for name, content in previous.items():
        (tmp_path / name).write_bytes(content)
    monkeypatch.setattr(svg, "chrome", lambda: "chrome")

    def browser(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
        shot = Path(next(arg.removeprefix("--screenshot=") for arg in args if arg.startswith("--screenshot=")))
        if failure == "timeout":
            raise subprocess.TimeoutExpired(args, 60)
        if failure == "empty-output":
            shot.touch()
        if failure == "second-render" and shot.name == "concept.png":
            shot.write_bytes(b"new brand screenshot")
        return subprocess.CompletedProcess(args, 0, b"", b"")

    monkeypatch.setattr(svg.subprocess, "run", browser)
    with pytest.raises((RuntimeError, subprocess.TimeoutExpired)):
        svg.render(source, tmp_path)
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == previous


@pytest.mark.skipif(
    sys.platform == "darwin",
    # Headless Chrome screenshots time out on GitHub's macOS runners (runs 38439557067, 38444198105);
    # the stubbed render tests above still cover macOS, and Linux CI runs this real-browser check.
    reason="headless Chrome screenshots hang on macOS CI runners",
)
def test_browser_blocks_scripts_and_network_without_changing_clean_pixels(svg: ModuleType, tmp_path: Path) -> None:
    try:
        binary = svg.chrome()
    except RuntimeError:
        pytest.skip("Chrome/Chromium is required for the direct-SVG browser regression")

    clean = tmp_path / "clean.svg"
    clean.write_bytes(TEMPLATE.read_bytes())
    fallback = tmp_path / "control-fallback.svg"
    fallback.write_text(svg.BRAND_FONTS.sub("", clean.read_text(encoding="utf-8")), encoding="utf-8")
    out = tmp_path / "shots"
    out.mkdir()

    def direct(source: Path, name: str) -> bytes:
        """Original screenshot command, with only synthetic test hosts routed locally."""
        shot = out / name
        with tempfile.TemporaryDirectory() as profile:
            result = subprocess.run(
                [
                    binary,
                    "--headless=new",
                    "--hide-scrollbars",
                    "--disable-gpu",
                    "--no-proxy-server",
                    "--host-resolver-rules=MAP svg-preview.test 127.0.0.1",
                    f"--user-data-dir={profile}",
                    "--window-size=960,420",
                    f"--screenshot={shot}",
                    source.resolve().as_uri(),
                ],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=60,
                check=False,
            )
        assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
        assert shot.is_file(), result.stderr.decode("utf-8", "replace")
        return shot.read_bytes()

    requests: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            requests.append(self.path)
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.end_headers()
            self.wfile.write(b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>')

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib handler signature
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            event = tmp_path / "event.svg"
            event.write_text(
                clean.read_text(encoding="utf-8").replace(
                    "<svg ",
                    "<svg onload=\"document.querySelector('rect').style.fill='magenta'\" ",
                    1,
                ),
                encoding="utf-8",
            )
            network = tmp_path / "network.svg"
            network.write_text(
                clean.read_text(encoding="utf-8").replace(
                    "</svg>",
                    "".join(
                        f'<image href="http://{host}:{server.server_port}/{host}" width="1" height="1"/>'
                        for host in ("localhost", "127.0.0.1", "svg-preview.test")
                    )
                    + "</svg>",
                ),
                encoding="utf-8",
            )
            original = direct(clean, "original.png")
            original_fallback = direct(fallback, "original-fallback.png")
            # A synchronous pixel change proves script execution; <image> below proves network
            # access without racing an asynchronous request against screenshot process exit.
            assert direct(event, "active.png") != original
            direct(network, "network-control.png")
            assert set(requests) == {"/localhost", "/127.0.0.1", "/svg-preview.test"}
            requests.clear()

            # Bypass the authoring checks to exercise the browser boundary itself.
            for source in (clean, event, network):
                shots = svg.render(source, out)
                assert len(shots) == 2
                if source != network:
                    assert shots[0].read_bytes() == original
                    assert shots[1].read_bytes() == original_fallback
                assert requests == []
        finally:
            server.shutdown()
            thread.join()


def test_missing_file_fails(svg: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert svg.main([str(tmp_path / "absent.svg")]) == 1
    assert "file not found" in capsys.readouterr().out
