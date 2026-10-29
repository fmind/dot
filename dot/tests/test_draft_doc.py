"""Exercise the Google Docs native Markdown (.md) and figure compiler."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "skills/draft-doc/scripts/compile_markdown_doc.py"

VALID_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 220" role="img" aria-labelledby="title desc">
  <title id="title">Figure 1 — Summary Card</title>
  <desc id="desc">Summary card showing 3 metrics on a 600x220 canvas.</desc>
  <rect width="600" height="220" rx="16" fill="#FFFFFF"/>
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
        ("# Heading\n\nParagraph without blank line\n---\n", "Setext heading underline"),
        ("# Heading\n\n**Bold lead-in**\n---\n", "Setext heading underline"),
        ("# Heading\n\nTitle\n===\n", "Setext heading underline"),
        ("# Heading\n\nBefore\n\n<!-- note -->\n", "Raw HTML tag"),
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


@pytest.mark.parametrize("snippet", ["1. item\n---\n", "- item\n  more\n---\n", "> quote\n---\n", "***\n---\n"])
def test_check_markdown_dialect_allows_thematic_break_after_blocks(mod: ModuleType, snippet: str) -> None:
    # CommonMark: a setext underline is never a lazy continuation line, so `---` here is a horizontal rule.
    assert mod.check_markdown_dialect(f"# Heading\n\n{snippet}") == []


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
    assert any("expected 600" in p for p in problems)
    assert any('role="img"' in p for p in problems)
    assert any("below 12px" in p for p in problems)
    assert any("<script> is ignored or unsafe" in p for p in problems)
    assert mod.check_svg(tmp_path / "missing.svg") == [f"{tmp_path / 'missing.svg'}: SVG file not found"]


def test_compile_markdown_replaces_mermaid_and_svg_with_base64_refs(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svg_file = tmp_path / "card.svg"
    svg_file.write_text(VALID_SVG, encoding="utf-8")

    def fake_mermaid(_code: str, out_png: Path, scale: float = 2, max_width_px: int | None = None) -> None:
        assert (scale, max_width_px) == (2, 600)
        out_png.write_bytes(b"FAKE_MERMAID_PNG")

    def fake_svg(_svg_path: Path, out_png: Path, scale: float = 2, max_width_px: int | None = None) -> tuple[int, int]:
        assert (scale, max_width_px) == (2, 600)
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

    def fake_render_svg(_svg_path: Path, out: Path, *, scale: float = 2, **_kwargs: object) -> tuple[int, int]:
        out.write_bytes(b"PNG")
        return (round(600 * scale), round(220 * scale))

    monkeypatch.setattr(mod, "render_svg_png", fake_render_svg)

    out_png = tmp_path / "card.png"
    assert mod.main([str(svg_file), "-o", str(out_png), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["dimensions_px"] == [1200, 440]

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


def test_cli_drive_upload_creates_assets_subfolder_and_upserts(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    svg_file = tmp_path / "card.svg"
    svg_file.write_text(VALID_SVG, encoding="utf-8")
    src_md = tmp_path / "memo.src.md"
    src_md.write_text("# Memo\n\n![Card](card.svg)\n", encoding="utf-8")

    def fake_render_svg(_svg_path: Path, out: Path, *, scale: float = 2, **_kwargs: object) -> tuple[int, int]:
        out.write_bytes(b"PNG")
        return (round(600 * scale), round(220 * scale))

    gws_calls: list[list[str]] = []

    def fake_run_gws(args: list[str]) -> dict[str, object]:
        gws_calls.append(args)
        if args[:3] == ["drive", "files", "list"]:
            params = json.loads(args[args.index("--params") + 1])
            q = params["q"]
            if "name = 'assets'" in q:
                return {"files": [{"id": "folder_assets_1", "name": "assets"}]}
            if "name = 'memo'" in q:
                return {"files": []}
            if "'folder_memo_assets_2' in parents" in q:
                return {"files": [{"id": "existing_svg_9", "name": "card.svg"}]}
            return {"files": []}
        if args[:3] == ["drive", "files", "create"]:
            body = json.loads(args[args.index("--json") + 1])
            if body.get("mimeType") == "application/vnd.google-apps.folder":
                return {"id": "folder_memo_assets_2", "name": body["name"]}
            return {
                "id": f"new_{body['name']}",
                "name": body["name"],
                "mimeType": body["mimeType"],
                "webViewLink": f"https://drive.google.com/file/d/new_{body['name']}/view",
            }
        if args[:3] == ["drive", "files", "update"]:
            params = json.loads(args[args.index("--params") + 1])
            assert "--json" not in args, "asset updates must not rename"
            return {"id": params["fileId"], "name": "card.svg", "mimeType": "image/svg+xml"}
        msg = f"Unexpected gws call: {args}"
        raise AssertionError(msg)

    monkeypatch.setattr(mod, "render_svg_png", fake_render_svg)
    monkeypatch.setattr(mod, "run_gws", fake_run_gws)

    assert (
        mod.main(
            [
                str(src_md),
                "--drive-folder",
                "parent_folder_123",
                "--doc-name",
                "Memo.md",
                "--doc-slug",
                "memo",
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    drive = payload["drive"]
    assert drive["file_id"] == "new_Memo.md"
    assert drive["docs_url"] == "https://docs.google.com/document/d/new_Memo.md/edit"
    assert drive["assets_folder_id"] == "folder_memo_assets_2"
    assert drive["assets_folder_path"] == "assets/memo"
    uploaded_by_name = {item["name"]: item["id"] for item in drive["uploaded_assets"]}
    assert uploaded_by_name == {
        "memo.src.md": "new_memo.src.md",
        "card.svg": "existing_svg_9",
        "fig-1.png": "new_fig-1.png",
    }

    with pytest.raises(ValueError, match="Invalid folder ID"):
        mod.upload_to_drive(tmp_path / "memo.md", [], drive_folder="bad id with spaces'; DROP")


def _png(width: int, height: int = 10) -> bytes:
    """Return a PNG signature and IHDR header, enough for png_size."""
    return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + width.to_bytes(4, "big") + height.to_bytes(4, "big")


def _fake_drive(calls: list[list[str]], *, doc_name: str = "Quarterly Review.md") -> object:
    """Fake gws for an existing document in folder_parent_1 whose assets folders are created on demand."""

    def fake_run_gws(args: list[str]) -> dict[str, object]:
        calls.append(args)
        params = json.loads(args[args.index("--params") + 1])
        if args[:3] == ["drive", "files", "get"]:
            return {"id": params["fileId"], "name": doc_name, "parents": ["folder_parent_1"]}
        if args[:3] == ["drive", "files", "list"]:
            return {"files": []}
        if args[:3] == ["drive", "files", "create"]:
            body = json.loads(args[args.index("--json") + 1])
            return {"id": f"new_{body['name']}", "name": body["name"], "mimeType": body["mimeType"]}
        if args[:3] == ["drive", "files", "update"]:
            body = json.loads(args[args.index("--json") + 1]) if "--json" in args else {}
            return {"id": params["fileId"], "name": body.get("name", doc_name), "mimeType": "text/markdown"}
        msg = f"Unexpected gws call: {args}"
        raise AssertionError(msg)

    return fake_run_gws


def test_cli_update_by_file_id_keeps_drive_name_and_asset_slug(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "card.svg").write_text(VALID_SVG, encoding="utf-8")
    src_md = tmp_path / "report.src.md"
    src_md.write_text("# Report\n\n![Card](card.svg)\n", encoding="utf-8")

    def fake_render_svg(_svg: Path, out: Path, **_kwargs: object) -> tuple[int, int]:
        out.write_bytes(_png(600))
        return (600, 138)

    calls: list[list[str]] = []
    monkeypatch.setattr(mod, "render_svg_png", fake_render_svg)
    monkeypatch.setattr(mod, "run_gws", _fake_drive(calls))

    out_md = tmp_path / "report.md"
    assert mod.main([str(src_md), "-o", str(out_md), "--file-id", "doc_file_42", "--json"]) == 0
    drive = json.loads(capsys.readouterr().out)["drive"]
    assert drive["name"] == "Quarterly Review.md"
    assert drive["assets_folder_path"] == "assets/Quarterly-Review"
    assert (tmp_path / "assets" / "Quarterly-Review" / "card.svg").is_file()
    doc_update = next(c for c in calls if c[:3] == ["drive", "files", "update"])
    assert "--json" not in doc_update, "updating by --file-id without --doc-name must not rename the document"
    folders = [json.loads(c[c.index("--json") + 1])["name"] for c in calls if c[:3] == ["drive", "files", "create"]]
    assert folders[:2] == ["assets", "Quarterly-Review"]


def test_upload_by_file_id_renames_only_with_doc_name(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compiled = tmp_path / "report.md"
    compiled.write_text("# Report\n", encoding="utf-8")
    calls: list[list[str]] = []
    monkeypatch.setattr(mod, "run_gws", _fake_drive(calls))

    result = mod.upload_to_drive(compiled, [], file_id="doc_file_42", doc_name="Final Report")
    update = next(c for c in calls if c[:3] == ["drive", "files", "update"])
    assert json.loads(update[update.index("--json") + 1]) == {"name": "Final Report.md"}
    assert result["name"] == "Final Report.md"


def test_upload_finds_existing_document_on_a_later_page(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compiled = tmp_path / "Memo.md"
    compiled.write_text("# Memo\n", encoding="utf-8")
    pages: dict[str | None, dict[str, object]] = {
        None: {"files": [{"id": "other_1", "name": "Other.md"}], "nextPageToken": "page2"},
        "page2": {"files": [{"id": "memo_2", "name": "Memo.md"}]},
    }
    calls: list[list[str]] = []

    def fake_run_gws(args: list[str]) -> dict[str, object]:
        calls.append(args)
        params = json.loads(args[args.index("--params") + 1])
        if args[:3] == ["drive", "files", "list"]:
            assert "nextPageToken" in params["fields"]
            return pages[params.get("pageToken")]
        if args[:3] == ["drive", "files", "update"]:
            return {"id": params["fileId"], "name": "Memo.md"}
        msg = f"Unexpected gws call: {args}"
        raise AssertionError(msg)

    monkeypatch.setattr(mod, "run_gws", fake_run_gws)
    assert mod.upload_to_drive(compiled, [], drive_folder="parent_folder_123")["file_id"] == "memo_2"
    assert [c[2] for c in calls] == ["list", "list", "update"]


@pytest.mark.parametrize("value", ["0", "-1", "5", "2.5", "big"])
def test_cli_rejects_invalid_scale(mod: ModuleType, tmp_path: Path, value: str) -> None:
    with pytest.raises(SystemExit) as excinfo:
        mod.main([str(tmp_path / "doc.md"), "--scale", value])
    assert excinfo.value.code == 2


def test_compile_markdown_rerun_reuses_svg_asset_name(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "card.svg").write_text(VALID_SVG, encoding="utf-8")

    def fake_svg(_svg: Path, out_png: Path, **_kwargs: object) -> tuple[int, int]:
        out_png.write_bytes(b"PNG")
        return (600, 138)

    monkeypatch.setattr(mod, "render_svg_png", fake_svg)
    assets_dir = tmp_path / "assets"
    for _ in range(2):
        _, figures = mod.compile_markdown("# Doc\n\n![Card](card.svg)\n", tmp_path, assets_dir=assets_dir)
        assert Path(figures[0]["source_asset"]).name == "card.svg"
    assert sorted(path.name for path in assets_dir.iterdir()) == ["card.svg", "fig-1.png"]


def test_render_mermaid_runs_pinned_cli_through_mise_and_caps_width(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs: object) -> object:
        commands.append(command)
        scale = float(command[command.index("-s") + 1])
        Path(command[command.index("-o") + 1]).write_bytes(_png(round(360 * scale)))
        return mod.subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(mod.shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    monkeypatch.setenv("PUPPETEER_EXECUTABLE_PATH", "/bin/chrome")
    out_png = tmp_path / "fig.png"
    mod.render_mermaid_png("flowchart LR\n  A --> B\n", out_png, scale=2, max_width_px=600)

    assert commands[0][:6] == ["/bin/mise", "exec", "--quiet", mod.MERMAID_CLI, "--", "mmdc"]
    assert "@mermaid-js/mermaid-cli" in mod.MERMAID_CLI
    assert [c[c.index("-s") + 1] for c in commands] == ["2", "1.66667"]
    assert mod.png_size(out_png) == (600, 10)
