from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from fmind_dot import skill_contracts as checker

ROOT = Path(__file__).parents[2]


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
        ("references/__pycache__/payload.pyc", b"generated", "Python bytecode cache"),
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

    assert any("not directly disclosed" in finding for finding in findings)
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


def test_skills_contract_skips_untracked_foreign_skill_root(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    target = root / "foreign"
    target.mkdir()
    (target / "SKILL.md").write_text("foreign package\n", encoding="utf-8")
    (root / "skills/foreign").symlink_to(target, target_is_directory=True)

    assert checker.repository_findings(root) == []


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


def test_skills_live_repository_contract() -> None:
    findings = checker.repository_findings(ROOT)

    assert findings == [], "\n".join(findings)


@pytest.mark.parametrize(
    "name",
    ["bootstrap.md", "profiles.md", "tooling.md"],
)
def test_python_stack_reference_links_are_document_relative(name: str) -> None:
    document = ROOT / "skills/python-stack/references" / name
    targets = [
        raw_target.strip().strip("<>").split(maxsplit=1)[0]
        for raw_target in checker.LINK_PATTERN.findall(document.read_text(encoding="utf-8"))
    ]
    missing = [
        target
        for target in targets
        if target
        and not target.startswith(("#", "{"))
        and ":" not in target.split("/", 1)[0]
        and not (document.parent / target.split("#", 1)[0].split("?", 1)[0]).exists()
    ]

    assert missing == []


def test_python_only_owned_sources_and_retired_tool_cleanup() -> None:
    retired_suffixes = {".go", ".js", ".jsx", ".ts", ".tsx"}
    owned = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, text=True
    ).splitlines()
    active = [path for path in owned if Path(path).suffix in retired_suffixes and (ROOT / path).exists()]

    assert active == []
    assert not (ROOT / "archives").exists()
    assert not (ROOT / "skills/hugo").exists()
    assert not [path for path in owned if Path(path).name.startswith("remove_") and (ROOT / path).exists()]


def test_deploy_uses_the_locked_python_runtime_graph() -> None:
    tasks = (ROOT / "mise.toml").read_text(encoding="utf-8")
    deploy = (ROOT / "dot/src/fmind_dot/deploy.py").read_text(encoding="utf-8")

    assert (
        'run = "\\"$(mise which python)\\" -I dot/src/fmind_dot/deploy.py \\"$PWD\\" \\"$(mise which uv)\\""' in tasks
    )
    assert "uv run --project dot --frozen python dot/src/fmind_dot/deploy.py" not in tasks
    assert "uv run --frozen python dot/src/fmind_dot/deploy.py" not in tasks
    assert '"--locked",' in deploy
    assert '"--require-hashes",' in deploy
    assert '"--only-binary",' in deploy
    assert '"--strict",' in deploy
    assert "--no-hashes" not in deploy
    assert "uv tool install" not in tasks
    assert "from fmind_dot.system import write_install_receipt" in deploy
    assert 'DOT_BIN = "{{env.HOME}}/.local/share/fmind-dot/current/bin/dot"' in tasks
    assert "run = '\"$DOT_BIN\" completion'" in tasks
    assert "run = '\"$DOT_BIN\" verify'" in tasks
    assert (
        (ROOT / "dot_local/bin/symlink_dot.tmpl")
        .read_text(encoding="utf-8")
        .endswith("/.local/share/fmind-dot/current/bin/dot\n")
    )
