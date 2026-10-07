from __future__ import annotations

import fnmatch
import os
import shutil
import subprocess
import tomllib
from collections.abc import Callable
from pathlib import Path

import pytest

from dot_tasks import skill_contracts as checker
from dot_tasks.mise_locks import LOCK_REVISION, bundle
from dot_tasks.mise_refresh import validate

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


def _fixture_repository(tmp_path: Path) -> Path:
    _write_skill(tmp_path)
    _write_skill(
        tmp_path,
        name="fixture-helper",
        description="Support compact fixtures. Use when contract tests need a second route.",
    )
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
    # Without markers, format:skills cannot rewrite the index, so the finding names the markers.
    path.write_text(path.read_text().replace(checker.GUIDE_START, "").replace(checker.GUIDE_END, ""))
    assert any("add <!-- guides:start -->" in item for item in checker.repository_findings(root))


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
    findings, _ = checker._skill_findings(root, "child", promoted)
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
    outstanding: set[str] = set()
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


def test_global_lock_covers_every_configured_native_platform() -> None:
    # The refresh task's own gate: versions, downloads, checksums, and dependency graphs.
    validate(ROOT / "dot_config/mise")


def test_repository_mise_lock_includes_valid_dependency_files() -> None:
    lock = ROOT / "mise.lock"
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
