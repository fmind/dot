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


def test_apply_individual_skills_preserves_other_packages(
    installation: tuple[Path, Path, list[str]],
) -> None:
    source, home, command = installation
    package = source / "skills/python-stack"
    catalog = home / ".agents/skills"
    catalog.mkdir(parents=True)
    independent = home / "independent"
    independent.mkdir()
    (catalog / "meeting-prep").symlink_to(independent, target_is_directory=True)
    for _ in range(2):
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        assert result.stderr == ""
        assert not catalog.is_symlink()
        assert (catalog / "python-stack").is_symlink()
        assert (catalog / "python-stack").resolve() == package
        assert (package / "SKILL.md").read_text() == "# Fixture\n"
        assert (catalog / "meeting-prep").resolve() == independent
        assert not (source / "skills/meeting-prep").exists()

    # A later repository-name collision fails even with --force and preserves the owner.
    (catalog / "python-stack").unlink()
    (catalog / "python-stack").symlink_to(independent, target_is_directory=True)
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode != 0
    assert "belongs to another source" in result.stderr
    assert (catalog / "python-stack").resolve() == independent


def test_apply_rejects_former_whole_catalog_link(installation: tuple[Path, Path, list[str]]) -> None:
    source, home, command = installation
    catalog = home / ".agents/skills"
    catalog.parent.mkdir()
    catalog.symlink_to(source / "skills", target_is_directory=True)
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode != 0
    assert "must be a real directory" in result.stderr
    assert catalog.is_symlink()
    assert (source / "skills/python-stack/SKILL.md").read_text() == "# Fixture\n"


def test_catalog_migration_restores_context_checks_after_upgrade(
    installation: tuple[Path, Path, list[str]],
) -> None:
    from dot_tasks.skill_links import migrate_links
    from fmind_dot.context_budget import context_report
    from fmind_dot.errors import DotError

    source, home, command = installation
    current = source / "skills/python-stack/SKILL.md"
    current.write_text("---\nname: python-stack\ndescription: Python fixture.\n---\n")
    old = source / "skills/typer"
    old.mkdir()
    (old / "SKILL.md").write_text("---\nname: typer\ndescription: Old fixture.\n---\n")
    declaration = source / "dot_agents/skills/symlink_typer.tmpl"
    declaration.write_text("{{ .chezmoi.sourceDir }}/skills/typer\n")
    subprocess.run(command, capture_output=True, check=True)
    declaration.unlink()
    shutil.rmtree(old)
    subprocess.run(command, capture_output=True, check=True)
    link = home / ".agents/skills/typer"
    with pytest.raises(DotError, match="broken skill link"):
        context_report(home, global_root=home / ".agents")
    assert migrate_links(source, home) is None
    assert link.is_symlink()
    assert not (home / ".agents/retired-skill-links").exists()
    backup = migrate_links(source, home, apply=True)
    assert backup is not None
    assert (backup / "typer").readlink() == old
    assert not link.is_symlink()
    assert context_report(home, global_root=home / ".agents")["passed"]
    assert migrate_links(source, home, apply=True) is None
    assert list(backup.parent.iterdir()) == [backup]


@pytest.mark.parametrize("replacement", ["file", "directory", "foreign-link", "active"])
def test_catalog_migration_preserves_other_owners_and_reactivated_names(
    installation: tuple[Path, Path, list[str]], replacement: str
) -> None:
    from dot_tasks.skill_links import migrate_links

    source, home, _command = installation
    link = home / ".agents/skills/typer"
    link.parent.mkdir(parents=True)
    if replacement == "file":
        link.write_text("another owner")
    elif replacement == "directory":
        link.mkdir()
        (link / "owned.txt").write_text("another owner")
    else:
        target = source / "skills/typer" if replacement == "active" else home / "another-owner"
        link.symlink_to(target)
        if replacement == "active":
            (source / "dot_agents/skills/symlink_typer.tmpl").write_text("active\n")
    before = link.lstat()
    assert migrate_links(source, home, apply=True) is None
    assert link.lstat() == before


def test_catalog_migration_rejects_linked_backup_parent(
    installation: tuple[Path, Path, list[str]],
) -> None:
    from dot_tasks.skill_links import migrate_links
    from fmind_dot.errors import DotError

    source, home, _command = installation
    link = home / ".agents/skills/typer"
    link.parent.mkdir(parents=True)
    link.symlink_to(source / "skills/typer")
    (home / ".agents/retired-skill-links").symlink_to(home / "elsewhere")
    with pytest.raises(DotError, match="backup parent must be a real directory"):
        migrate_links(source, home, apply=True)
    assert link.readlink() == source / "skills/typer"


def test_catalog_migration_interruption_preserves_backup_and_retries_remaining_links(
    installation: tuple[Path, Path, list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    from dot_tasks.skill_links import migrate_links
    from fmind_dot.errors import DotError

    source, home, _command = installation
    catalog = home / ".agents/skills"
    catalog.mkdir(parents=True)
    for name in ("typer", "uv"):
        (catalog / name).symlink_to(source / "skills" / name)
    rename = Path.rename

    def interrupt(path: Path, target: str | Path) -> Path:
        if path.name == "uv":
            raise OSError("synthetic interrupted move")
        return rename(path, target)

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "rename", interrupt)
        with pytest.raises(DotError, match="completed moves remain recoverable"):
            migrate_links(source, home, apply=True)
    first = next((home / ".agents/retired-skill-links").iterdir())
    assert (first / "typer").readlink() == source / "skills/typer"
    assert (catalog / "uv").is_symlink()
    second = migrate_links(source, home, apply=True)
    assert second is not None
    assert second != first
    assert (second / "uv").readlink() == source / "skills/uv"
    assert (first / "typer").readlink() == source / "skills/typer"
    assert not list(catalog.iterdir())
