"""Exercise the login-shell modify templates against empty, existing, and second-pass targets."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.chezmoi_helpers import chezmoi

ROOT = Path(__file__).resolve().parents[2]
MODIFIERS = {
    "modify_dot_bashrc": ("# chezmoi: mise-bash-path", "mise activate bash"),
    "modify_dot_profile": ("# chezmoi: mise-bash-integration", "export PATH="),
    "modify_dot_zprofile": ("# chezmoi: mise-zsh-integration", "mise activate zsh"),
}


def render(tmp_path: Path, modifier: str, content: str) -> str:
    # apply consumes the modify-template directive; execute-template needs it removed.
    directive, template = (ROOT / modifier).read_text(encoding="utf-8").split("\n", 1)
    assert directive == "# chezmoi:modify-template"
    template_path = tmp_path / "input.tmpl"
    template_path.write_text(template, encoding="utf-8")
    source = tmp_path / "source"
    shutil.copytree(ROOT / ".chezmoitemplates", source / ".chezmoitemplates", dirs_exist_ok=True)
    return chezmoi(source, "execute-template", "--with-stdin", "--file", str(template_path), stdin=content)


@pytest.mark.parametrize("modifier", sorted(MODIFIERS))
@pytest.mark.parametrize("existing", ["", "export FOO=1\n"], ids=["empty", "existing"])
def test_modifier_preserves_target_and_is_repeatable(tmp_path: Path, modifier: str, existing: str) -> None:
    sentinel, activation = MODIFIERS[modifier]
    first = render(tmp_path, modifier, existing)
    assert existing.strip() in first
    assert first.count(sentinel) == 1
    assert first.count(activation) == 1
    assert "Docs:" not in first
    # Shell installers append with `>>`; a missing newline would merge their line into the block.
    assert first.splitlines()[-1].startswith("# chezmoi: end mise-")
    assert first.endswith("\n")
    assert render(tmp_path, modifier, first) == first


@pytest.mark.parametrize("modifier", sorted(MODIFIERS))
def test_modifier_rewrites_stale_block_in_place(tmp_path: Path, modifier: str) -> None:
    sentinel, _activation = MODIFIERS[modifier]
    end = sentinel.replace("chezmoi: ", "chezmoi: end ")
    current = render(tmp_path, modifier, "export BEFORE=1\n")
    stale = current.replace(f"{sentinel}\n", f"{sentinel}\n# stale line\n") + "export AFTER=1\n"
    rewritten = render(tmp_path, modifier, stale)
    assert rewritten == current + "export AFTER=1\n"
    assert rewritten.count(end) == 1


def test_modifier_ignores_prefix_and_orphan_end_markers(tmp_path: Path) -> None:
    prefix = "# chezmoi: mise-bash-integration-extra\nexport EXTRA=1\n# chezmoi: end mise-bash-integration-extra\n"
    rendered = render(tmp_path, "modify_dot_profile", prefix)
    assert prefix in rendered
    assert rendered.count("# chezmoi: mise-bash-integration\n") == 1
    orphan_end = "export USER_VAR=1\n# chezmoi: end mise-bash-integration\n"
    with_orphan = render(tmp_path, "modify_dot_profile", orphan_end)
    assert "# chezmoi: mise-bash-integration\n" in with_orphan
    assert "export USER_VAR=1\n" in with_orphan


def test_macos_only_targets_are_ignored_elsewhere() -> None:
    ignore = (ROOT / ".chezmoiignore").read_text(encoding="utf-8")
    _, block = ignore.split('{{- if ne .chezmoi.os "darwin" }}\n', 1)
    # zsh login profile and the Docker plugin config for the mise-installed macOS Docker stack.
    assert block.split("{{- end }}", 1)[0].split() == [".docker", ".zprofile"]
    _, linux_block = ignore.split('{{- if ne .chezmoi.os "linux" }}\n', 1)
    assert linux_block.split("{{- end }}", 1)[0].split() == [".config/systemd", "systemd-user-reload.sh"]


@pytest.mark.parametrize("shell", ["sh", "bash"])
def test_profile_only_exposes_mise_shims(tmp_path: Path, shell: str) -> None:
    profile = render(tmp_path, "modify_dot_profile", "")
    assert "mise activate" not in profile
    environment = {key: value for key, value in os.environ.items() if key != "BASH_VERSION"}
    environment.update(HOME=str(tmp_path), PATH="/usr/bin:/bin")
    command = profile + '\nprintf "%s\\n" "$PATH"\n'
    result = subprocess.run(
        [shell, "-c", command], env=environment, capture_output=True, text=True, check=False, timeout=30
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith(f"{tmp_path}/.local/share/mise/shims:")


def test_profile_keeps_bashrc_activation_ahead_of_shims(tmp_path: Path) -> None:
    profile = render(tmp_path, "modify_dot_profile", "")
    # Debian-style .profile sources .bashrc first, whose activation already placed tools before the shims.
    activated = f"{tmp_path}/.local/share/mise/installs/python/bin:/usr/bin:{tmp_path}/.local/share/mise/shims:/bin"
    environment = {key: value for key, value in os.environ.items() if key != "BASH_VERSION"}
    environment.update(HOME=str(tmp_path), PATH=activated)
    result = subprocess.run(
        ["sh", "-c", profile + '\nprintf "%s\\n" "$PATH"\n'],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == activated
