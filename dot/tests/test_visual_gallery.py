"""Exercise the variant contact sheet without a real browser."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "skills/fmind-visuals/scripts/gallery.py"
SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10"/></svg>'


@pytest.fixture
def gallery() -> ModuleType:
    spec = importlib.util.spec_from_file_location("visual_gallery", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_labels_keep_round_numbers_and_skip_the_sheet(gallery: ModuleType, tmp_path: Path) -> None:
    for name in ("v14-blue.svg", "v3-red.svg", "sketch.svg", "gallery.png", "notes.txt"):
        (tmp_path / name).write_text(SVG)
    labels = [label for label, _ in gallery.variants(tmp_path)]
    assert labels == ["#1", "v14", "v03"]


def test_sheet_is_self_contained_and_escapes_names(gallery: ModuleType, tmp_path: Path) -> None:
    (tmp_path / "v01-<b>.svg").write_text(SVG)
    page = gallery.sheet(tmp_path, "Logo & mark")
    assert "data:image/svg+xml;base64," in page
    assert "Logo &amp; mark" in page
    assert "v01-&lt;b&gt;.svg" in page
    assert page.count('class="light"') == page.count('class="dark"') == 1


def test_empty_or_oversized_folders_fail(gallery: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert gallery.main([str(tmp_path)]) == 1
    (tmp_path / "v01.svg").write_text(SVG)
    monkeypatch.setattr(gallery, "LIMIT", 10)
    with pytest.raises(ValueError, match="embed as at least"):
        gallery.sheet(tmp_path, "Variants")


def test_limit_applies_to_the_written_page(
    gallery: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "v01.svg").write_text(SVG)
    size = len(gallery.sheet(tmp_path, "Variants").encode())
    raw = len(SVG.encode())
    assert size > raw * 8 // 3  # the page outgrows its inputs: two base64 copies plus markup
    monkeypatch.setattr(gallery, "LIMIT", size - 1)  # inputs pass the pre-check, the page does not
    with pytest.raises(ValueError, match=rf"sheet is {size} bytes.*split the folder"):
        gallery.sheet(tmp_path, "Variants")
    assert gallery.main([str(tmp_path)]) == 1
    assert not (tmp_path / "gallery.html").exists()
    monkeypatch.setattr(gallery, "LIMIT", size)
    assert gallery.main([str(tmp_path)]) == 0
    assert (tmp_path / "gallery.html").stat().st_size == size


def test_png_uses_the_configured_browser(gallery: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    browser = tmp_path / "chrome"
    browser.write_text(
        f"#!{sys.executable}\n"
        "import sys\nfrom pathlib import Path\n"
        "shot=next(a.split('=',1)[1] for a in sys.argv if a.startswith('--screenshot='))\n"
        "Path(shot).write_bytes(b'png')\n"
    )
    browser.chmod(0o700)
    folder = tmp_path / "round"
    folder.mkdir()
    (folder / "v01.svg").write_text(SVG)
    monkeypatch.setenv("CHROME", str(browser))
    assert gallery.main([str(folder), "--png"]) == 0
    assert (folder / "gallery.html").exists()
    assert (folder / "gallery.png").read_bytes() == b"png"
