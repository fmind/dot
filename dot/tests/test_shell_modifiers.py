"""Exercise the login-shell modify templates against empty, existing, and second-pass targets."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODIFIERS = {
    "modify_dot_bashrc": ("# chezmoi: mise-bash-path", "mise activate bash"),
    "modify_dot_profile": ("# chezmoi: mise-bash-integration", "export PATH="),
    "modify_dot_zprofile": ("# chezmoi: mise-zsh-integration", "mise activate zsh"),
}


def render(tmp_path: Path, modifier: str, content: str) -> str:
    chezmoi = shutil.which("chezmoi")
    assert chezmoi is not None, "chezmoi is required for shell modifier tests"
    # apply consumes the modify-template directive; execute-template needs it removed.
    directive, template = (ROOT / modifier).read_text(encoding="utf-8").split("\n", 1)
    assert directive == "# chezmoi:modify-template"
    template_path = tmp_path / "input.tmpl"
    template_path.write_text(template, encoding="utf-8")
    config = tmp_path / "chezmoi.toml"
    config.write_text("", encoding="utf-8")
    source = tmp_path / "source"
    shutil.copytree(ROOT / ".chezmoitemplates", source / ".chezmoitemplates", dirs_exist_ok=True)
    command = [chezmoi, "--source", str(source), "--destination", str(tmp_path), "--config", str(config)]
    command += ["execute-template", "--with-stdin", "--file", str(template_path)]
    result = subprocess.run(command, input=content, encoding="utf-8", capture_output=True, check=False, timeout=30)
    assert result.returncode == 0, result.stderr
    return result.stdout


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


def test_zprofile_is_deployed_only_on_macos() -> None:
    ignore = (ROOT / ".chezmoiignore").read_text(encoding="utf-8")
    assert '{{- if ne .chezmoi.os "darwin" }}\n.zprofile\n{{- end }}' in ignore


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
