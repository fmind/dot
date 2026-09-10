"""Repository skill links coexist with other packages in the standard catalog."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def installation(tmp_path: Path) -> tuple[Path, Path, list[str]]:
    source, home = tmp_path / "source", tmp_path / "home"
    source.mkdir()
    home.mkdir()
    (source / ".chezmoiignore").write_text('{{ includeTemplate "skill-catalog-check.tmpl" . }}\nskills\n')
    (source / ".chezmoitemplates").mkdir()
    shutil.copyfile(
        ROOT / ".chezmoitemplates/skill-catalog-check.tmpl", source / ".chezmoitemplates/skill-catalog-check.tmpl"
    )
    package = source / "skills/python-stack"
    package.mkdir(parents=True)
    (package / "SKILL.md").write_text("# Fixture\n")
    declarations = source / "dot_agents/skills"
    declarations.mkdir(parents=True)
    shutil.copyfile(ROOT / "dot_agents/skills/symlink_python-stack.tmpl", declarations / "symlink_python-stack.tmpl")
    config = tmp_path / "chezmoi.toml"
    config.write_text("")
    return (
        source,
        home,
        [
            "chezmoi",
            "--source",
            str(source),
            "--destination",
            str(home),
            "--config",
            str(config),
            "--persistent-state",
            str(tmp_path / "state.boltdb"),
            "apply",
            "--force",
        ],
    )


@pytest.mark.parametrize("rename", [False, True])
def test_retired_repository_links_need_explicit_cleanup(
    installation: tuple[Path, Path, list[str]], rename: bool
) -> None:
    source, home, command = installation
    subprocess.run(command, capture_output=True, text=True, check=True)
    catalog = home / ".agents/skills"
    peer = catalog / "meeting-prep"
    peer.mkdir()
    (peer / "SKILL.md").write_text("# Another package\n")
    (source / "dot_agents/skills/symlink_python-stack.tmpl").unlink()
    if rename:
        (source / "skills/python-stack").rename(source / "skills/python-workflow")
        (source / "dot_agents/skills/symlink_python-workflow.tmpl").write_text(
            "{{ .chezmoi.sourceDir }}/skills/python-workflow\n"
        )
    subprocess.run([*command, "--dry-run"], capture_output=True, text=True, check=True)
    assert (catalog / "python-stack").is_symlink()
    for _ in range(2):
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        assert result.stderr == ""
        assert (catalog / "python-stack").is_symlink()
        assert (peer / "SKILL.md").read_text() == "# Another package\n"
        name = "python-workflow" if rename else "python-stack"
        assert (source / "skills" / name / "SKILL.md").read_text() == "# Fixture\n"
        if rename:
            assert (catalog / name).resolve() == source / "skills" / name

    target = catalog / "python-stack"
    # Removal remains an explicit, owner-checked action outside dot's runtime.
    assert target.is_symlink()
    assert target.readlink() == source / "skills/python-stack"
    backup = home / "retired-python-stack"
    target.rename(backup)
    assert backup.readlink() == source / "skills/python-stack"
    assert not target.is_symlink()
    assert (peer / "SKILL.md").read_text() == "# Another package\n"


@pytest.mark.parametrize("replacement", ["directory", "link", "dangling-link", "file"])
def test_apply_preserves_retired_names_now_owned_elsewhere(
    installation: tuple[Path, Path, list[str]], replacement: str
) -> None:
    source, home, command = installation
    subprocess.run(command, capture_output=True, text=True, check=True)
    (source / "dot_agents/skills/symlink_python-stack.tmpl").unlink()
    target = home / ".agents/skills/python-stack"
    target.unlink()
    elsewhere = home / "library/python-stack"
    if replacement == "directory":
        target.mkdir()
        (target / "SKILL.md").write_text("# Another owner\n")
    elif replacement == "file":
        target.write_text("preserve")
    else:
        if replacement == "link":
            elsewhere.mkdir(parents=True)
            (elsewhere / "SKILL.md").write_text("# Another owner\n")
        target.symlink_to(elsewhere)
    subprocess.run(command, capture_output=True, text=True, check=True)
    if replacement.endswith("link"):
        assert target.readlink() == elsewhere
    elif replacement == "directory":
        assert (target / "SKILL.md").read_text() == "# Another owner\n"
    else:
        assert target.read_text() == "preserve"


def test_source_relocation_requires_explicit_link_repair(installation: tuple[Path, Path, list[str]]) -> None:
    source, home, command = installation
    subprocess.run(command, capture_output=True, text=True, check=True)
    moved = source.with_name("moved-source")
    source.rename(moved)
    command[command.index("--source") + 1] = str(moved)
    target = home / ".agents/skills/python-stack"
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode != 0
    assert "belongs to another source" in result.stderr
    assert target.readlink() == source / "skills/python-stack"
    target.unlink()
    subprocess.run(command, capture_output=True, text=True, check=True)
    assert target.readlink() == moved / "skills/python-stack"
    assert (target / "SKILL.md").read_text() == "# Fixture\n"


@pytest.mark.parametrize("conflict", ["directory", "file", "dangling-link", "catalog-link"])
def test_apply_blocks_conflicting_skill_owners(installation: tuple[Path, Path, list[str]], conflict: str) -> None:
    _source, home, command = installation
    catalog = home / ".agents/skills"
    catalog.mkdir(parents=True)
    target = catalog / "python-stack"
    if conflict == "directory":
        target.mkdir()
        (target / "SKILL.md").write_text("preserve")
    elif conflict == "file":
        target.write_text("preserve")
    elif conflict == "dangling-link":
        target.symlink_to(home / "missing")
    else:
        catalog.rmdir()
        elsewhere = home / "elsewhere"
        elsewhere.mkdir()
        catalog.symlink_to(elsewhere)
        target.write_text("preserve")
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode != 0
    if conflict == "dangling-link":
        assert target.readlink() == home / "missing"
    elif conflict == "directory":
        assert (target / "SKILL.md").read_text() == "preserve"
    else:
        assert target.read_text() == "preserve"


@pytest.mark.parametrize("existing_catalog", [False, True])
def test_apply_individual_skills_preserves_other_packages(
    installation: tuple[Path, Path, list[str]], existing_catalog: bool
) -> None:
    source, home, command = installation
    package = source / "skills/python-stack"
    catalog = home / ".agents/skills"
    catalog.parent.mkdir()
    independent = home / "independent"
    independent.mkdir()
    if existing_catalog:
        # Exercise replacement of the former whole-catalog symlink.
        catalog.symlink_to(source / "skills", target_is_directory=True)
    else:
        catalog.mkdir()
        (catalog / "meeting-prep").symlink_to(independent, target_is_directory=True)
    if existing_catalog:
        foreign = source / "skills/meeting-prep"
        foreign.symlink_to(independent, target_is_directory=True)
        blocked = subprocess.run(command, capture_output=True, text=True, check=False)
        assert blocked.returncode != 0
        assert "legacy catalog contains separately installed links" in blocked.stderr
        assert catalog.is_symlink()
        assert foreign.resolve() == independent
        foreign.unlink()
    for _ in range(2):
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        assert result.stderr == ""
        assert not catalog.is_symlink()
        assert (catalog / "python-stack").is_symlink()
        assert (catalog / "python-stack").resolve() == package
        assert (package / "SKILL.md").read_text() == "# Fixture\n"
        if not existing_catalog:
            assert (catalog / "meeting-prep").resolve() == independent
        assert not (source / "skills/meeting-prep").exists()

    # A later repository-name collision fails even with --force and preserves the owner.
    (catalog / "python-stack").unlink()
    (catalog / "python-stack").symlink_to(independent, target_is_directory=True)
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode != 0
    assert "belongs to another source" in result.stderr
    assert (catalog / "python-stack").resolve() == independent
