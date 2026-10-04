from __future__ import annotations

import fnmatch
import json
import os
import shutil
import subprocess
import tomllib
from collections.abc import Callable
from pathlib import Path

import pytest

from dot_tasks import skill_contracts as checker
from dot_tasks.mise_locks import LOCK_REVISION, bundle

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


def _fixture_repository(tmp_path: Path) -> Path:
    _write_skill(tmp_path)
    _write_skill(
        tmp_path,
        name="fixture-helper",
        description="Support compact fixtures. Use when contract tests need a second route.",
    )
    _write_contract_files(tmp_path)
    (tmp_path / "README.md").write_text("# Fixture\n\nPython implementation.\n", encoding="utf-8")
    (tmp_path / "dot_agents").mkdir()
    (tmp_path / "dot_agents/AGENTS.md").write_text("# Fixture instructions\n", encoding="utf-8")
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
        ("references/tags.md", "safe\U000e0069\U000e0067hidden\n".encode(), "invisible Unicode"),
        ("references/selectors.md", "safe\ufe00\U000e0100hidden\n".encode(), "invisible Unicode"),
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


def test_repository_skills_have_individual_chezmoi_links() -> None:
    packages = {path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md")}
    links = ROOT / "dot_agents/skills"
    assert {path.name for path in links.iterdir()} == {f"symlink_{name}.tmpl" for name in packages}
    for name in packages:
        assert (links / f"symlink_{name}.tmpl").read_text() == "{{ .chezmoi.sourceDir }}/skills/" + name + "\n"


def test_skills_contract_enforces_catalog_references(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    manifest = json.loads((root / "skills/contracts.json").read_text(encoding="utf-8"))
    manifest["skills"]["archived-stack"] = []
    (root / "skills/contracts.json").write_text(json.dumps(manifest), encoding="utf-8")

    findings = checker.repository_findings(root)

    assert any("registered skill 'archived-stack' has no active SKILL.md" in finding for finding in findings)


def test_documentation_checks_root_and_security_policy_links(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    (root / "README.md").write_text("[Configuration](dot_config/dot.yaml)\n")
    (root / ".github").mkdir(exist_ok=True)
    (root / ".github/SECURITY.md").write_text("[Retired section](../README.md#missing)\n")

    findings = checker.documentation_findings(root)

    assert any("README.md: missing local link 'dot_config/dot.yaml'" in finding for finding in findings)
    assert any(".github/SECURITY.md: missing local anchor '../README.md#missing'" in finding for finding in findings)


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


def test_skills_contract_fails_on_duplicate_declared_skill_names(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
    # Directory names are unique, so a nested package is how a declared name can repeat.
    nested = root / "skills/fixture-helper/extra/fixture/SKILL.md"
    nested.parent.mkdir(parents=True)
    nested.write_text((root / "skills/fixture/SKILL.md").read_text())
    findings = checker.repository_findings(root)
    assert any(
        finding.startswith("agent context: duplicate skill name 'fixture' in ")
        and "skills/fixture/SKILL.md" in finding
        and "skills/fixture-helper/extra/fixture/SKILL.md" in finding
        and "Rename one skill or remove a copy" in finding
        for finding in findings
    ), findings


def test_skills_contract_does_not_budget_the_combined_total(tmp_path: Path) -> None:
    root = _fixture_repository(tmp_path)
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
def test_skills_rejects_unknown_kind(tmp_path: Path, kind: str) -> None:
    root = _fixture_repository(tmp_path)
    skill = root / "skills/fixture/SKILL.md"
    skill.write_text(skill.read_text().replace("kind: task", f"kind: {kind}"))
    assert any("metadata.kind must" in item for item in checker.repository_findings(root))


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


def test_python_only_owned_sources_and_retired_tool_cleanup() -> None:
    retired_suffixes = {".go", ".js", ".jsx", ".ts", ".tsx"}
    owned = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, text=True
    ).splitlines()
    active = [path for path in owned if Path(path).suffix in retired_suffixes and (ROOT / path).exists()]

    assert active == []
    # Removal markers stay only until every workstation has applied them; list each
    # outstanding one here and delete it (and its entry) once it has shipped.
    outstanding = {
        "dot_config/dot/private_secrets/remove_JULES_API_KEY",
        "dot_config/dot/private_secrets/remove_UV_PUBLISH_TOKEN",
        "dot_config/fish/conf.d/remove_secrets.fish",
        "dot_config/nvim/lua/plugins/remove_prose.lua",
        "dot_copilot/hooks/remove_notify.json",
    }
    markers = {path for path in owned if Path(path).name.startswith("remove_") and (ROOT / path).exists()}
    assert markers == outstanding


@pytest.mark.skipif(shutil.which("fish") is None, reason="fish is not installed")
@pytest.mark.parametrize("fetched", [False, True])
def test_fzf_theme_file_is_exported_only_once_fetched(tmp_path: Path, fetched: bool) -> None:
    # fzf exits 2 on a missing FZF_DEFAULT_OPTS_FILE, and a targeted or offline apply skips externals.
    theme = tmp_path / ".config/fzf/theme.conf"
    if fetched:
        theme.parent.mkdir(parents=True)
        theme.touch()
    env = {key: value for key, value in os.environ.items() if key != "FZF_DEFAULT_OPTS_FILE"} | {"HOME": str(tmp_path)}
    script = "source $argv[1]; set -q FZF_DEFAULT_OPTS_FILE; and echo $FZF_DEFAULT_OPTS_FILE"
    result = subprocess.run(
        ["fish", "--no-config", "-c", script, ROOT / "dot_config/fish/conf.d/fzf.fish"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.stdout.strip() == (str(theme) if fetched else "")


def test_deploy_uses_the_locked_python_runtime_graph() -> None:
    config = tomllib.loads((ROOT / "mise.toml").read_text(encoding="utf-8"))
    tasks = config["tasks"]
    commands = {
        name: " ".join([run] if isinstance(run := task.get("run", []), str) else run) for name, task in tasks.items()
    }

    # Deployment bootstraps from the mise-selected interpreter in isolated mode; going
    # through `uv run` would make the installer depend on the environment it replaces.
    assert '$(mise which python)" -I dot/src/fmind_dot/deploy.py' in commands["deploy"]
    assert "$(mise which uv)" in commands["deploy"]
    assert not [name for name, command in commands.items() if "deploy.py" in command and "uv run" in command]
    assert not [name for name, command in commands.items() if "uv tool install" in command]
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


# Their registry entries publish no checksum; keep in step with config.toml.tmpl's comment.
UNCHECKSUMMED_GLOBAL_TOOLS = frozenset({"acli", "awscli", "gcloud", "sonarqube-cli", "ttyd"})


def test_global_lock_covers_every_configured_native_platform() -> None:
    rendered = subprocess.check_output(
        [
            "chezmoi",
            "execute-template",
            "--source",
            str(ROOT),
            "--file",
            str(ROOT / "dot_config/mise/config.toml.tmpl"),
        ],
        text=True,
        timeout=30,
    )
    config = tomllib.loads(rendered)
    document = tomllib.loads((ROOT / "dot_config/mise/mise.lock").read_text(encoding="utf-8"))
    platforms = config["settings"]["lockfile_platforms"]
    assert platforms
    findings: list[str] = []
    for name, settings in config["tools"].items():
        version = settings.get("version", "") if isinstance(settings, dict) else settings
        if isinstance(version, str) and version.startswith("path:"):
            continue  # Machine-local runtime overrides do not belong in the shared lock.
        if not document["tools"].get(name):
            findings.append(f"{name}: not locked")
        if name.startswith(("npm:", "pipx:")):
            continue  # Native dependency graphs are validated by bundle() below.
        entries = document["tools"].get(name, [])
        allowed_os = settings.get("os") if isinstance(settings, dict) else None
        for platform in platforms:
            if allowed_os and platform.split("-")[0] not in allowed_os:
                continue
            # Platform-specific asset options produce separate lock entries, so
            # each supported platform needs one complete artifact across them.
            artifacts = [entry.get(f"platforms.{platform}", {}) for entry in entries]
            if not any(artifact.get("url") for artifact in artifacts):
                findings.append(f"{name} {platform}: no url")
            checksummed = any(
                str(artifact.get("checksum", "")).startswith(("sha256:", "sha512:", "blake3:"))
                for artifact in artifacts
            )
            if checksummed == (name in UNCHECKSUMMED_GLOBAL_TOOLS):
                findings.append(
                    f"{name} {platform}: checksum {'now available; drop the exemption' if checksummed else 'missing'}"
                )
    assert findings == [], "\n".join(findings)


@pytest.mark.parametrize("relative", ["mise.lock", "dot_config/mise/mise.lock"])
def test_mise_locks_include_valid_dependency_files(relative: str) -> None:
    lock = ROOT / relative
    document = tomllib.loads(lock.read_text())
    assert document["lockfile_version"] == LOCK_REVISION
    files = bundle(lock)
    for name, entries in document["tools"].items():
        for entry in entries:
            assert entry["version"]
            if name.startswith(("npm:", "pipx:")):
                assert {"uv", "aube"}.intersection(entry), name
    assert all((lock.parent / path).is_file() for path in files)


def test_encrypted_targets_are_ignored_without_the_age_key(tmp_path: Path) -> None:
    # A host without the owner's age key must skip every encrypted source, not fail apply.
    # Render from a minimal copy: scanning the live checkout races with parallel test files.
    source, home = tmp_path / "source", tmp_path / "home"
    home.mkdir()
    shutil.copytree(ROOT / ".chezmoitemplates", source / ".chezmoitemplates")
    shutil.copy2(ROOT / ".chezmoiignore", source / ".chezmoiignore")
    listed = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", "--", "*.age"], check=True, capture_output=True, timeout=30
    )
    encrypted = [Path(name.decode()) for name in listed.stdout.split(b"\0") if name]
    assert encrypted
    for relative in encrypted:
        (source / relative).parent.mkdir(parents=True, exist_ok=True)
        (source / relative).touch()
    config = tmp_path / "chezmoi.toml"
    config.write_text("")
    common = ["--source", str(source), "--config", str(config), "--destination", str(home)]
    environment = {**os.environ, "HOME": str(home)}

    def chezmoi(*arguments: str) -> list[str]:
        command = ["chezmoi", *arguments[:1], *common, *arguments[1:]]
        result = subprocess.run(command, env=environment, check=True, capture_output=True, text=True, timeout=30)
        return result.stdout.splitlines()

    patterns = [line.strip() for line in chezmoi("execute-template", "--file", str(source / ".chezmoiignore"))]
    patterns = [pattern for pattern in patterns if pattern and not pattern.startswith(("#", "!"))]
    unignored = []
    for target in chezmoi("target-path", *(str(source / relative) for relative in encrypted)):
        relative = Path(target).relative_to(home).as_posix().removesuffix(".age")
        if not any(
            relative == pattern or relative.startswith(f"{pattern}/") or fnmatch.fnmatchcase(relative, pattern)
            for pattern in patterns
        ):
            unignored.append(relative)
    assert unignored == [], "add these encrypted targets to the no-key block in .chezmoiignore"


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
