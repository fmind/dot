"""Exercise the Google Docs native Markdown (.md) and @2x figure compiler."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "skills/draft-doc/scripts/compile_markdown_doc.py"

VALID_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 220" role="img" aria-labelledby="title desc">
  <title id="title">Figure 1 — Summary Card</title>
  <desc id="desc">Summary card showing 3 metrics on a 960x220 canvas.</desc>
  <rect width="960" height="220" rx="16" fill="#FFFFFF"/>
  <text x="32" y="48" font-size="18" fill="#202124">Summary Card</text>
  <text x="32" y="80" font-size="12" fill="#595D62">Subtitle text</text>
</svg>
"""


@pytest.fixture
def mod() -> ModuleType:
    spec = importlib.util.spec_from_file_location("compile_markdown_doc", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_check_markdown_dialect_accepts_clean_doc(mod: ModuleType) -> None:
    md = (
        "# Nightly Batch Architecture Review\n\n"
        "Type: Decision memo\\\n"
        "Status: Draft\n\n"
        "> **Important — Decision needed by 2026-11-15:** Approve Option 2.\n\n"
        "## Executive summary\n\n"
        "**Moving nightly batch jobs to spot virtual machines reduces compute spend by 60%.**\n\n"
        "---\n\n"
        "- [x] Validate retry backoff (`<details>` and `> [!IMPORTANT]` inside inline code are ignored)\n"
        "- [ ] Deploy policy gate\n\n"
        "![Figure 1 — Summary Card][fig-1]\n\n"
        "```python\n"
        "def verify() -> bool:\n"
        '    return "<details>" != ""\n'
        "```\n\n"
        "[fig-1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==>\n"
    )
    assert mod.check_markdown_dialect(md) == []


@pytest.mark.parametrize(
    ("snippet", "expected"),
    [
        ("---\ntitle: Doc\n---\n\n# Heading\n", "YAML frontmatter"),
        ("# Heading\n\nParagraph without blank line\n---\n", "Setext H2 underline"),
        ("# Heading\n\n> [!IMPORTANT]\n> Act now.\n", "GitHub Alert syntax"),
        ("# Heading\n\n<details><summary>More</summary>Text</details>\n", "Raw HTML tag"),
        ("# Heading\n\nLine one<br>Line two\n", "Raw HTML tag"),
        ("# Heading\n\n```mermaid\nflowchart LR\n  A --> B\n```\n", "Uncompiled ```mermaid block"),
        ("# Heading\n\n![Card](card.svg)\n", "Uncompiled .svg image link"),
    ],
)
def test_check_markdown_dialect_rejects_unsupported_constructs(
    mod: ModuleType,
    snippet: str,
    expected: str,
) -> None:
    problems = mod.check_markdown_dialect(snippet)
    assert any(expected in p for p in problems), problems


def test_check_svg_validates_contract(mod: ModuleType, tmp_path: Path) -> None:
    svg_file = tmp_path / "valid.svg"
    svg_file.write_text(VALID_SVG, encoding="utf-8")
    assert mod.check_svg(svg_file) == []

    bad_svg = tmp_path / "bad.svg"
    bad_svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 200"><text font-size="9">tiny</text><script>alert(1)</script></svg>',
        encoding="utf-8",
    )
    problems = mod.check_svg(bad_svg)
    assert any("expected 960" in p for p in problems)
    assert any('role="img"' in p for p in problems)
    assert any("below minimum 12px" in p for p in problems)
    assert any("<script> is forbidden" in p for p in problems)


def test_compile_markdown_replaces_mermaid_and_svg_with_base64_refs(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svg_file = tmp_path / "card.svg"
    svg_file.write_text(VALID_SVG, encoding="utf-8")

    def fake_mermaid(_code: str, out_png: Path, scale: int = 2) -> None:
        assert scale == 2
        out_png.write_bytes(b"FAKE_MERMAID_PNG")

    def fake_svg(_svg_path: Path, out_png: Path, scale: int = 2) -> tuple[int, int]:
        assert scale == 2
        out_png.write_bytes(b"FAKE_SVG_PNG")
        return (1920, 440)

    monkeypatch.setattr(mod, "render_mermaid_png", fake_mermaid)
    monkeypatch.setattr(mod, "render_svg_png", fake_svg)

    source_md = (
        "# Architecture Proposal\n\n"
        "```mermaid\n"
        "%% alt: Figure 1 — Request Pipeline\n"
        "flowchart LR\n"
        "  A --> B\n"
        "```\n\n"
        "![Figure 2 — KPI Summary Card](card.svg)\n\n"
        "Inline code `![ignored](other.svg)` stays untouched.\n"
    )

    assets_dir = tmp_path / "assets"
    compiled, figures = mod.compile_markdown(source_md, tmp_path, assets_dir=assets_dir)
    assert "```mermaid" not in compiled
    assert "(card.svg)" not in compiled
    assert "`![ignored](other.svg)`" in compiled
    assert "![Figure 1 — Request Pipeline][fig-1]" in compiled
    assert "![Figure 2 — KPI Summary Card][fig-2]" in compiled
    assert "[fig-1]: <data:image/png;base64,RkFLRV9NRVJNQUlEX1BORw==>" in compiled
    assert "[fig-2]: <data:image/png;base64,RkFLRV9TVkdfUE5H>" in compiled
    assert len(figures) == 2
    assert figures[0]["kind"] == "mermaid"
    assert Path(figures[0]["source_asset"]).read_text(encoding="utf-8").startswith("%% alt:")
    assert Path(figures[0]["png_asset"]).read_bytes() == b"FAKE_MERMAID_PNG"
    assert figures[1]["kind"] == "svg"
    assert Path(figures[1]["source_asset"]).name == "card.svg"
    assert Path(figures[1]["png_asset"]).read_bytes() == b"FAKE_SVG_PNG"


def test_cli_json_check_and_compile(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    svg_file = tmp_path / "card.svg"
    svg_file.write_text(VALID_SVG, encoding="utf-8")

    def fake_render_svg(_svg_path: Path, out: Path, *, scale: int = 2) -> tuple[int, int]:
        out.write_bytes(b"PNG")
        return (960 * scale, 220 * scale)

    monkeypatch.setattr(mod, "render_svg_png", fake_render_svg)

    out_png = tmp_path / "card.png"
    assert mod.main([str(svg_file), "-o", str(out_png), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["dimensions_px"] == [1920, 440]

    src_md = tmp_path / "memo.src.md"
    src_md.write_text("# Memo\n\n![Card](card.svg)\n", encoding="utf-8")
    out_md = tmp_path / "memo.md"
    bundle_dir = tmp_path / "bundle"
    assert mod.main([str(src_md), "-o", str(out_md), "--assets-dir", str(bundle_dir), "--json"]) == 0
    md_payload = json.loads(capsys.readouterr().out)
    assert md_payload["assets_dir"] == str(bundle_dir)
    assert str(bundle_dir / "memo.src.md") in md_payload["assets"]
    assert str(bundle_dir / "card.svg") in md_payload["assets"]
    assert str(bundle_dir / "fig-1.png") in md_payload["assets"]

    bad_md = tmp_path / "bad.md"
    bad_md.write_text("---\ntitle: Bad\n---\n# Title\n", encoding="utf-8")
    assert mod.main([str(bad_md), "--check-only", "--json"]) == 1
    err_payload = json.loads(capsys.readouterr().err)
    assert "YAML frontmatter" in err_payload["error"]
