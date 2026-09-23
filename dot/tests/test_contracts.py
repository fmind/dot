from __future__ import annotations

import json
import os
import subprocess
import tomllib
from collections.abc import Callable
from pathlib import Path

import pytest

from dot_tasks import skill_contracts as checker
from dot_tasks.mise_locks import bundle

ROOT = Path(__file__).resolve().parents[2]


def _write_skill(
    root: Path,
    *,
    name: str = "fixture",
    description: str = "Validate a compact fixture. Use for skill contract tests.",
) -> Path:
    directory = root / "skills" / name
    directory.mkdir(parents=True)
    skill = directory / "SKILL.md"
    skill.write_text(
        "---\n"
        f"name: {name}\n"
        f"description: {description}\n"
        "license: MIT\n"
        "metadata:\n"
        "  kind: task\n"
        "  author: Fixture Author\n"
        "---\n\n"
        "# Fixture\n\n"
        "Validate a fixture with the uv executable.\n\n"
        "## Workflow\n\n"
        "1. Run the fixture.\n\n"
        "## Documentation\n\n"
        "- [Reference](references/guide.md)\n",
        encoding="utf-8",
    )
    references = directory / "references"
    references.mkdir()
    (references / "guide.md").write_text("# Guide\n", encoding="utf-8")
    return skill


def _write_contract_files(root: Path) -> None:
    contracts = {"version": 1, "skills": {"fixture": ["uv"], "fixture-helper": []}}
    path = root / "skills" / "contracts.json"
    path.write_text(json.dumps(contracts), encoding="utf-8")
    routing = root / "dot" / "testdata" / "skills" / "routing-boundaries.json"
    routing.parent.mkdir(parents=True)
    routing.write_text(
        json.dumps(
            {
                "version": 1,
                "created": "2026-09-06",
                "purpose": "Exercise routing fixture structure.",
                "construction": "Cover routed, multi-intent, and abstaining cases.",
                "proof_boundary": "This fixture does not prove host routing.",
                "cases": [
                    {
                        "id": "fixture-route",
                        "categories": ["contract"],
                        "prompt": "Run the compact fixture validation workflow for this package.",
                        "expected": ["fixture"],
                        "primary": "fixture",
                        "top_k": 3,
                    },
                    {
                        "id": "fixture-multi",
                        "categories": ["multi-intent"],
                        "prompt": "Validate the fixture and document the same fixture result.",
                        "expected": ["fixture", "fixture-helper"],
                        "primary": "fixture",
                        "top_k": 3,
                        "require_all_top_k": 5,
                    },
                    {
                        "id": "fixture-helper-route",
                        "categories": ["contract"],
                        "prompt": "Run the helper workflow independently for this routing fixture.",
                        "expected": ["fixture-helper"],
                        "primary": "fixture-helper",
                        "top_k": 3,
                    },
                    {
                        "id": "fixture-abstain",
                        "categories": ["no-route"],
                        "prompt": "Translate this ordinary sentence into French without changing it.",
                        "route": False,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def _fixture_repository(tmp_path: Path) -> Path:
    _write_skill(tmp_path)
    _write_skill(
        tmp_path,
        name="fixture-helper",
        description="Support compact fixtures. Use when contract tests need a second route.",
    )
    _write_contract_files(tmp_path)
    (tmp_path / "README.md").write_text("# Fixture\n\nPython implementation.\n", encoding="utf-8")
    return tmp_path


def test_skills_contract_accepts_small_valid_repository(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)

    assert checker.repository_findings(root) == []


@pytest.mark.parametrize("value", ["true", "false", '"true"', "1", "null"])
def test_skills_contract_checks_explicit_invocation_boolean(tmp_path: Path, value: str) -> None:
    root = _fixture_repository(tmp_path)
    skill = root / "skills/fixture/SKILL.md"
    skill.write_text(skill.read_text().replace("license: MIT", f"license: MIT\ndisable-model-invocation: {value}"))

    findings = checker.repository_findings(root)
    if value in {"true", "false"}:
        assert findings == []
    else:
        assert any("disable-model-invocation must be a boolean" in finding for finding in findings)


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (lambda text: text.replace("name: fixture", "name: wrong"), "must match its directory"),
        (lambda text: text.replace("# Fixture", "Fixture"), "H1 heading"),
        (lambda text: text.replace("## ", "### "), "H2 section"),
        (lambda text: text.replace("(references/guide.md)", "(references/missing.md)"), "missing local link"),
        (lambda text: text.replace("uv executable", "package executable"), "required tool 'uv' is undocumented"),
    ],
)
def test_skills_contract_rejects_broken_package(tmp_path: Path, mutation: Callable[[str], str], expected: str) -> None:
    root = _fixture_repository(tmp_path)
    skill = root / "skills/fixture/SKILL.md"
    skill.write_text(mutation(skill.read_text(encoding="utf-8")), encoding="utf-8")

    assert any(expected in finding for finding in checker.repository_findings(root))


@pytest.mark.parametrize(
    ("relative", "content", "expected"),
    [
        ("references/.pytest_cache/README.md", b"generated", "generated cache or metadata"),
        ("references/control.md", b"safe\x1b[2Jspoofed\n", "unsafe control character"),
        ("references/bidi.md", "safe\u202ehidden\n".encode(), "invisible Unicode"),
        ("references/binary.md", b"text\x00payload\n", "unsafe control character"),
        ("references/non-utf8.md", b"text\xffpayload\n", "is not UTF-8"),
        ("references/oversized.md", b"x" * ((1 << 20) + 1), "parsed-file limit"),
    ],
)
def test_skills_contract_rejects_unsafe_resources(tmp_path: Path, relative: str, content: bytes, expected: str) -> None:
    root = _fixture_repository(tmp_path)
    resource = root / "skills/fixture" / relative
    resource.parent.mkdir(parents=True, exist_ok=True)
    resource.write_bytes(content)

    assert any(expected in finding for finding in checker.repository_findings(root))


def test_skills_contract_rejects_unsafe_root_text(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    skill = root / "skills/fixture/SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8") + "\nHidden\u202etext\n", encoding="utf-8")

    assert any("invisible Unicode" in finding for finding in checker.repository_findings(root))


def test_skills_contract_rejects_undisclosed_and_misplaced_resources(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    skill = root / "skills/fixture"
    (skill / "references/hidden.md").write_text("# Hidden\n", encoding="utf-8")
    executable = skill / "assets/generator"
    executable.parent.mkdir()
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    executable.chmod(0o755)

    findings = checker.repository_findings(root)

    assert any("not reachable" in finding for finding in findings)
    assert any("executable outside scripts" in finding for finding in findings)


def test_skills_contract_rejects_non_regular_and_symlinked_resources(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    skill = root / "skills/fixture"
    target = skill / "outside.py"
    target.write_text("print('outside')\n", encoding="utf-8")
    script = skill / "scripts/payload.py"
    script.parent.mkdir()
    script.symlink_to(target)
    pipe = skill / "references/runtime.pipe"
    os.mkfifo(pipe)

    findings = checker.repository_findings(root)

    assert any("symbolic link" in finding for finding in findings)
    assert any("non-regular resource" in finding for finding in findings)


def test_skills_contract_parses_commonmark_and_html_links(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    skill = root / "skills/fixture/SKILL.md"
    skill.write_text(
        skill.read_text(encoding="utf-8")
        + "\nRead [missing][detail].\n\n[detail]: references/missing.md\n"
        + '<img src="references/missing.png">\n',
        encoding="utf-8",
    )

    findings = checker.repository_findings(root)

    assert any("references/missing.md" in finding for finding in findings)
    assert any("references/missing.png" in finding for finding in findings)


def test_skills_contract_parses_nested_markdown_and_html_srcset_links(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    guide = root / "skills/fixture/references/guide.md"
    guide.write_text(
        '# Guide\n\n[Missing](missing.md)\n\n<img srcset="missing-small.png 1x, missing-large.png 2x">\n',
        encoding="utf-8",
    )

    findings = checker.repository_findings(root)

    assert any("missing.md" in finding for finding in findings)
    assert any("missing-small.png" in finding for finding in findings)
    assert any("missing-large.png" in finding for finding in findings)


def test_skills_contract_rejects_skill_root_relative_link_from_nested_document(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    guide = root / "skills/fixture/references/guide.md"
    guide.write_text("# Guide\n\n[Wrong root-relative link](SKILL.md)\n", encoding="utf-8")

    findings = checker.repository_findings(root)

    assert any("references/guide.md: missing local link 'SKILL.md'" in finding for finding in findings)


def test_skills_contract_accepts_html_metadata_and_srcset_url_commas(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    skill = root / "skills/fixture/SKILL.md"
    skill.write_text(
        skill.read_text(encoding="utf-8")
        + '\n<div data="metadata">value</div>\n<img srcset="https://example.com/a,b.png 1x">\n',
        encoding="utf-8",
    )

    assert checker.repository_findings(root) == []


@pytest.mark.parametrize(
    "markup",
    [
        '<a href="file&#58;///etc/passwd">outside</a>',
        '<object data="file:///etc/passwd"></object>',
        '<img srcset="https://example.com/image.png 1x, file:///etc/passwd 2x">',
    ],
)
def test_skills_contract_rejects_unsafe_html_targets(tmp_path: Path, markup: str) -> None:
    root = _fixture_repository(tmp_path)
    skill = root / "skills/fixture/SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8") + f"\n{markup}\n", encoding="utf-8")

    assert any("unsupported local link" in finding for finding in checker.repository_findings(root))


def test_skills_contract_rejects_repository_escape(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    skill = root / "skills/fixture/SKILL.md"
    skill.write_text(
        skill.read_text(encoding="utf-8") + "\n[Outside](../../../outside.md)\n",
        encoding="utf-8",
    )

    assert any("escapes the repository" in finding for finding in checker.repository_findings(root))


def test_skills_contract_rejects_symlinked_skill_root(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    target = root / "outside"
    target.mkdir()
    (target / "SKILL.md").write_text("---\nname: linked\ndescription: Linked fixture.\n---\n", encoding="utf-8")
    (root / "skills/linked").symlink_to(target, target_is_directory=True)

    assert any("symbolic link" in finding for finding in checker.repository_findings(root))


def test_skills_contract_rejects_untracked_foreign_skill_root(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    target = root / "foreign"
    target.mkdir()
    (target / "SKILL.md").write_text("foreign package\n", encoding="utf-8")
    (root / "skills/foreign").symlink_to(target, target_is_directory=True)

    assert any("symbolic link" in finding for finding in checker.repository_findings(root))


def test_skills_contract_rejects_root_with_files_but_no_entrypoint(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    (root / "skills/empty/references").mkdir(parents=True)
    assert checker.repository_findings(root) == []

    (root / "skills/orphan/references").mkdir(parents=True)
    (root / "skills/orphan/references/guide.md").write_text("# Orphan\n", encoding="utf-8")

    assert checker.repository_findings(root) == ["skills/orphan: skill root has files but no SKILL.md"]


def test_skills_contract_rejects_retired_skill_names_as_link_labels(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    skill = root / "skills/fixture/SKILL.md"
    (root / "skills/fixture/references/uv.md").write_text("# uv\n", encoding="utf-8")
    skill.write_text(
        skill.read_text(encoding="utf-8")
        + "- [uv](references/uv.md) keeps its name as a guide; [uv](https://docs.astral.sh/uv/) names the tool.\n",
        encoding="utf-8",
    )
    assert checker.repository_findings(root) == []

    skill.write_text(
        skill.read_text(encoding="utf-8") + "- [terraform](../fixture-helper/SKILL.md)\n",
        encoding="utf-8",
    )

    findings = checker.repository_findings(root)
    assert len(findings) == 1
    assert "link label 'terraform' is a retired skill name" in findings[0]


def test_repository_skills_have_individual_chezmoi_links() -> None:
    packages = {path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md")}
    links = ROOT / "dot_agents/skills"
    assert {path.name for path in links.iterdir()} == {f"symlink_{name}.tmpl" for name in packages}
    for name in packages:
        assert (links / f"symlink_{name}.tmpl").read_text() == "{{ .chezmoi.sourceDir }}/skills/" + name + "\n"
    assert not (ROOT / "dot_agents/symlink_skills.tmpl").exists()
    assert not (ROOT / "dot_agents/exact_skills").exists()


def test_skills_contract_enforces_catalog_and_routing_references(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    manifest = json.loads((root / "skills/contracts.json").read_text(encoding="utf-8"))
    manifest["skills"]["archived-stack"] = []
    (root / "skills/contracts.json").write_text(json.dumps(manifest), encoding="utf-8")
    routing_path = root / "dot/testdata/skills/routing-boundaries.json"
    routing = json.loads(routing_path.read_text(encoding="utf-8"))
    routing["cases"][0]["expected"] = ["archived-stack"]
    routing["cases"][0]["primary"] = "archived-stack"
    routing_path.write_text(json.dumps(routing), encoding="utf-8")

    findings = checker.repository_findings(root)

    assert any("registered skill 'archived-stack' has no active SKILL.md" in finding for finding in findings)
    assert any("referenced skill 'archived-stack' is absent" in finding for finding in findings)


def test_skills_contract_requires_a_primary_probe_for_every_active_skill(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    routing_path = root / "dot/testdata/skills/routing-boundaries.json"
    routing = json.loads(routing_path.read_text(encoding="utf-8"))
    routing["cases"] = [case for case in routing["cases"] if case.get("primary") != "fixture-helper"]
    routing_path.write_text(json.dumps(routing), encoding="utf-8")

    findings = checker.repository_findings(root)

    assert any("active skills without a primary routing probe: fixture-helper" in finding for finding in findings)


def test_skills_documentation_rejects_active_polyglot_claims_but_allows_explicit_exceptions(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    readme = root / "README.md"
    readme.write_text(
        "# Fixture\n\n"
        "The active CLI is implemented in Go and tested here.\n"
        "The former TypeScript implementation remains in git history.\n"
        "A third-party Go runtime remains supported by an external integration.\n",
        encoding="utf-8",
    )

    findings = checker.documentation_findings(root)

    assert len(findings) == 1
    assert "active Go or TypeScript implementation claim" in findings[0]


def test_documentation_checks_root_and_cli_readme_links(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    (root / "README.md").write_text("[Configuration](dot_config/dot.yaml)\n")
    (root / "dot/README.md").write_text("[Missing reference](missing.md)\n")

    findings = checker.documentation_findings(root)

    assert any("README.md: missing local link 'dot_config/dot.yaml'" in finding for finding in findings)
    assert any("dot/README.md: missing local link 'missing.md'" in finding for finding in findings)


def test_documentation_validates_markdown_fragments(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    readme = root / "README.md"
    readme.write_text(
        "# Fixture\n\n"
        "[Self](#fixture) [Code](guide.md#run-dot) [Unicode](guide.md#caf%C3%A9) "
        "[Duplicate](guide.md#repeat-1) [HTML](guide.md#explicit) "
        "[Missing](guide.md#removed) [Missing self](#gone)\n"
    )
    (root / "guide.md").write_text(
        '# Run `dot`\n\n## Café\n\n## Repeat\n\n## Repeat\n\n<a id="explicit"></a>\n```markdown\n# Not an anchor\n```\n'
    )
    findings = checker.documentation_findings(root)
    assert len(findings) == 2
    assert any("missing local anchor 'guide.md#removed'" in finding for finding in findings)
    assert any("missing local anchor '#gone'" in finding for finding in findings)
    readme.write_text("[Code block](guide.md#not-an-anchor)\n")
    assert "missing local anchor" in checker.documentation_findings(root)[0]


def test_skills_generated_template_fragments_are_not_checked_before_rendering(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    template = root / "skills/fixture/templates/README.md"
    template.parent.mkdir()
    template.write_text("[Replace when rendered](#generated-section)\n")
    assert checker._link_findings(root, root, documents=(template,)) == []


def test_skills_overlap_report_is_informational(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    routing = json.loads((root / "dot/testdata/skills/routing-boundaries.json").read_text(encoding="utf-8"))
    routing["cases"][0]["prompt"] = "Completely unrelated vocabulary about weather forecasts and beaches."
    (root / "dot/testdata/skills/routing-boundaries.json").write_text(json.dumps(routing), encoding="utf-8")

    report = checker.overlap_report(root)

    assert "informational only" in report
    assert "fixture-route" in report
    assert checker.repository_findings(root) == []


def test_skills_overlap_keeps_short_tool_names() -> None:
    assert {"d2", "hf", "ty", "uv", "xh"} <= checker._words("Use D2, hf, ty, uv, and xh.")


@pytest.mark.parametrize(("scope", "relative"), [("global", "dot_agents/AGENTS.md"), ("local", "AGENTS.md")])
def test_skills_contract_budgets_instructions_in_each_scope(tmp_path: Path, scope: str, relative: str) -> None:
    root = _fixture_repository(tmp_path)
    local = root / ".agents/skills"
    local.mkdir(parents=True)
    (root / "skills/fixture-helper").rename(local / "fixture-helper")
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x" * 20_000)
    findings = checker.repository_findings(root)
    assert any(f"{scope} AGENTS.md + skill discovery contains" in finding for finding in findings)
    assert not any(
        f"{'local' if scope == 'global' else 'global'} AGENTS.md + skill discovery contains" in finding
        for finding in findings
    )
    path.write_text("Short instructions.\n")
    assert checker.repository_findings(root) == []


def test_skills_contract_does_not_budget_the_combined_total(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    (root / "dot_agents").mkdir()
    (root / "dot_agents/AGENTS.md").write_text("g" * 12_000)
    (root / "AGENTS.md").write_text("p" * 12_000)
    assert checker.repository_findings(root) == []


def test_skills_catalog_report_is_portable_and_includes_name_and_path_cost(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    report = checker.catalog_report(root)
    assert "Global skills: 2; local skills: 0" in report
    assert "Global AGENTS.md + skill discovery:" in report
    assert "Local AGENTS.md + skill discovery:" in report
    assert " / <5000" in report
    assert "characters / 4" in report
    assert "not host tokenization or billing" in report
    assert str(tmp_path) not in report


@pytest.mark.parametrize("details", [False, True])
def test_skills_report_details_are_opt_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], details: bool
) -> None:
    root = _fixture_repository(tmp_path)
    monkeypatch.setattr(checker, "__file__", str(root / "dot/dot_tasks/skill_contracts.py"))
    monkeypatch.setattr("sys.argv", ["skill_contracts", "--report", *(["--details"] if details else [])])

    assert checker.main() == 0

    output = capsys.readouterr().out
    assert "Combined estimated index tokens:" in output
    assert "(informational)" in output
    assert "Discovery headroom:" not in output
    assert "Lexical rank-1 matches:" in output
    assert ("fixture-route" in output) is details
    assert ("- task: fixture, fixture-helper" in output) is details
    assert str(tmp_path) not in output


@pytest.mark.parametrize("slug", ["../escape", "", "guide, guide"])
def test_skills_contract_rejects_invalid_guide_metadata(tmp_path: Path, slug: str) -> None:
    root = _fixture_repository(tmp_path)
    path = root / "skills/fixture/SKILL.md"
    path.write_text(
        path.read_text().replace("  author: Fixture Author", f'  author: Fixture Author\n  guides: "{slug}"')
    )
    assert any("guide" in finding for finding in checker.repository_findings(root))


def test_skills_guide_metadata_drives_index_and_detects_stale_description(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    path = root / "skills/fixture/SKILL.md"
    guide = path.parent / "references/guide.md"
    guide.write_text("---\nname: guide\ndescription: Diagnose a fixture failure.\n---\n# Guide\n")
    path.write_text(path.read_text() + "\n" + checker._guide_index(path.parent, root) + "\n")
    assert checker.repository_findings(root) == []
    guide.write_text(guide.read_text().replace("Diagnose a fixture failure.", "Recover a fixture after interruption."))
    assert any("stale guide index" in item for item in checker.repository_findings(root))


def test_skills_nested_resources_are_reachable_but_disconnected_cycles_are_not(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    folder = root / "skills/fixture/references"
    (folder / "guide.md").write_text("# Guide\n\n[Procedure](procedure.md)\n")
    (folder / "procedure.md").write_text("# Procedure\n\nUse [template](template.txt).\n")
    (folder / "template.txt").write_text("fixture output\n")
    assert checker.repository_findings(root) == []
    (folder / "orphan-a.md").write_text("[B](orphan-b.md)\n")
    (folder / "orphan-b.md").write_text("[A](orphan-a.md)\n")
    findings = checker.repository_findings(root)
    assert sum("not reachable" in item for item in findings) == 2


def test_skills_reject_nested_entrypoint_even_when_linked(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    path = root / "skills/fixture/references/child/SKILL.md"
    path.parent.mkdir()
    path.write_text("# Child\n")
    (path.parent.parent / "guide.md").write_text("[Child](child/SKILL.md)\n")
    assert any("nested SKILL.md enters host discovery" in item for item in checker.repository_findings(root))


def test_skills_checks_links_inside_code_disclosed_resources(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    path = root / "skills/fixture/references/guide.md"
    path.write_text("Read `details.md` for the exact procedure.\n")
    (path.parent / "details.md").write_text("[Missing](missing.md)\n")
    assert any("details.md: missing local link" in item for item in checker.repository_findings(root))


@pytest.mark.parametrize("kind", ["unknown", "[]", "{}", "null"])
def test_skills_rejects_unknown_kind_and_foreign_guide_route(tmp_path: Path, kind: str) -> None:
    root = _fixture_repository(tmp_path)
    skill = root / "skills/fixture/SKILL.md"
    skill.write_text(skill.read_text().replace("kind: task", f"kind: {kind}"))
    routes = root / "dot/testdata/skills/routing-boundaries.json"
    data = json.loads(routes.read_text())
    data["cases"][0]["guide"] = "../../fixture-helper/references/guide.md"
    routes.write_text(json.dumps(data))
    findings = checker.repository_findings(root)
    assert any("metadata.kind must" in item for item in findings)
    assert any("guide must name" in item for item in findings)


def test_skills_guide_can_be_promoted_with_its_owned_resources(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    parent = root / "skills/fixture"
    guide = parent / "references/child/GUIDE.md"
    guide.parent.mkdir()
    guide.write_text(
        "---\nname: child\ndescription: Recover a fixture.\n---\n# Child\n\nRecover it.\n\n## Workflow\n\nUse [input](templates/input.txt).\n"
    )
    (guide.parent / "templates").mkdir()
    (guide.parent / "templates/input.txt").write_text("input\n")
    entry = parent / "SKILL.md"
    entry.write_text(entry.read_text() + "\n" + checker._guide_index(parent, root) + "\n")
    assert checker.repository_findings(root) == []
    destination = root / "skills/child"
    guide.parent.rename(destination)
    promoted = destination / "SKILL.md"
    (destination / "GUIDE.md").rename(promoted)
    promoted.write_text(
        promoted.read_text().replace(
            "description: Recover a fixture.", "description: Recover a fixture.\nlicense: MIT\nmetadata:\n  kind: task"
        )
    )
    findings, _ = checker._skill_findings(root, "child", promoted, [])
    assert findings == []
    assert (destination / "templates/input.txt").read_text() == "input\n"


def test_skills_live_repository_contract() -> None:
    findings = checker.repository_findings(ROOT)

    assert findings == [], "\n".join(findings)


def test_python_only_owned_sources_and_retired_tool_cleanup() -> None:
    retired_suffixes = {".go", ".js", ".jsx", ".ts", ".tsx"}
    owned = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, text=True
    ).splitlines()
    active = [path for path in owned if Path(path).suffix in retired_suffixes and (ROOT / path).exists()]

    assert active == []
    assert not (ROOT / "archives").exists()
    assert not (ROOT / "skills/hugo").exists()
    # Removal markers stay only until every workstation has applied them; list each
    # outstanding one here and delete it (and its entry) once it has shipped.
    outstanding = {"dot_copilot/hooks/remove_session-log.json"}
    markers = {path for path in owned if Path(path).name.startswith("remove_") and (ROOT / path).exists()}
    assert markers == outstanding


def test_deploy_uses_the_locked_python_runtime_graph() -> None:
    config = tomllib.loads((ROOT / "mise.toml").read_text(encoding="utf-8"))
    tasks = config["tasks"]
    deploy = (ROOT / "dot/src/fmind_dot/deploy.py").read_text(encoding="utf-8")
    commands = {
        name: " ".join([run] if isinstance(run := task.get("run", []), str) else run) for name, task in tasks.items()
    }

    # Deployment bootstraps from the mise-selected interpreter in isolated mode; going
    # through `uv run` would make the installer depend on the environment it replaces.
    assert '$(mise which python)" -I dot/src/fmind_dot/deploy.py' in commands["deploy"]
    assert "$(mise which uv)" in commands["deploy"]
    assert not [name for name, command in commands.items() if "deploy.py" in command and "uv run" in command]
    assert not [name for name, command in commands.items() if "uv tool install" in command]
    assert '"--locked",' in deploy
    assert '"--require-hashes",' in deploy
    assert '"--only-binary",' in deploy
    assert '"--strict",' in deploy
    assert "--no-hashes" not in deploy
    assert "from fmind_dot.deploy import write_install_receipt" in deploy
    # Workstation tasks run the deployed entrypoint, and it is the launcher chezmoi links.
    (launcher,) = (ROOT / "dot_local/bin").glob("symlink_*.tmpl")
    target = launcher.read_text(encoding="utf-8").strip().removeprefix("{{ .chezmoi.homeDir }}")
    assert config["env"]["DOT_BIN"] == "{{env.HOME}}" + target
    assert target.startswith("/.local/share/fmind-dot/current/bin/")
    for name in ("completions", "verify"):
        assert commands[name].startswith('"$DOT_BIN" '), name


def test_repository_lock_pins_every_tool_artifact_per_platform() -> None:
    config = tomllib.loads((ROOT / "mise.toml").read_text(encoding="utf-8"))
    document = tomllib.loads((ROOT / "mise.lock").read_text(encoding="utf-8"))
    platforms = {f"platforms.{platform}" for platform in config["settings"]["lockfile_platforms"]}
    assert platforms

    findings = [f"{name}: not locked" for name in config["tools"] if name not in document["tools"]]
    for name, entries in document["tools"].items():
        for entry in entries:
            for platform in sorted(platforms):
                artifact = entry.get(platform, {})
                if not artifact.get("url"):
                    findings.append(f"{name} {platform}: no url ({entry.get('backend')})")
                if not str(artifact.get("checksum", "")).startswith(("sha256:", "sha512:", "blake3:")):
                    findings.append(f"{name} {platform}: no checksum ({entry.get('backend')})")
    # Every tool must be verifiable from the lockfile alone: relock an unverifiable
    # tool on a checksummed backend (aqua, core, github) instead of exempting it.
    assert findings == [], "\n".join(findings)


@pytest.mark.parametrize("relative", ["mise.lock", "dot_config/mise/mise.lock"])
def test_mise_locks_include_valid_dependency_files(relative: str) -> None:
    lock = ROOT / relative
    document = tomllib.loads(lock.read_text())
    assert document["lockfile_version"] == 2
    files = bundle(lock)
    for name, entries in document["tools"].items():
        for entry in entries:
            assert entry["version"]
            if name.startswith(("npm:", "pipx:")):
                assert {"uv", "aube"}.intersection(entry), name
    assert all((lock.parent / path).is_file() for path in files)


# age's ASCII-armored and binary headers; the repository commits armored files.
_AGE_HEADERS = (b"-----BEGIN AGE ENCRYPTED FILE-----\n", b"age-encryption.org/v1\n")


def test_age_sources_are_encrypted() -> None:
    # Check the working candidate, including new sources and excluding deleted ones.
    # Read only the header; never decrypt or print credential contents.
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", "*.age"],
        cwd=ROOT,
        capture_output=True,
        check=True,
        timeout=30,
    ).stdout
    paths = [ROOT / name for name in listed.decode().split("\0") if name]
    paths = [path for path in paths if path.exists() or path.is_symlink()]
    assert paths, "expected encrypted chezmoi sources"
    plaintext = []
    for path in paths:
        assert not path.is_symlink(), "encrypted sources must be regular files"
        with path.open("rb") as stream:
            if not stream.read(64).startswith(_AGE_HEADERS):
                plaintext.append(path.relative_to(ROOT).as_posix())
    assert plaintext == [], "source .age files without an age header"
