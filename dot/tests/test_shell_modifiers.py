"""Exercise the login-shell modify templates against empty, existing, and second-pass targets."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODIFIERS = {
    "modify_dot_bashrc": ("# chezmoi: mise-bash-path", "mise activate bash"),
    "modify_dot_profile": ("# chezmoi: mise-bash-integration", "mise activate bash"),
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
    source.mkdir(exist_ok=True)
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
    assert render(tmp_path, modifier, first) == first


def test_zprofile_is_deployed_only_on_macos() -> None:
    ignore = (ROOT / ".chezmoiignore").read_text(encoding="utf-8")
    assert '{{- if ne .chezmoi.os "darwin" }}\n.zprofile\n{{- end }}' in ignore


@pytest.mark.parametrize("shell", ["sh", "bash"])
@pytest.mark.parametrize("previous_guard", [None, "", '[ -z "${CLAUDECODE:-}" ] && '])
def test_profile_supports_posix_login_and_migrates_bash_activation(
    tmp_path: Path, shell: str, previous_guard: str | None
) -> None:
    existing = ""
    if previous_guard is not None:
        existing = (
            "# chezmoi: mise-bash-integration\n"
            'export PATH="${HOME}/.local/bin:${PATH}"\n'
            f"if {previous_guard}command -v mise >/dev/null 2>&1; then\n"
            '  mise_activation="$(mise activate bash)"\n'
            '  eval "${mise_activation}"\n'
            "fi\n"
        )
    profile = render(tmp_path, "modify_dot_profile", existing)
    assert render(tmp_path, "modify_dot_profile", profile) == profile
    bin_directory = tmp_path / ".local/bin"
    bin_directory.mkdir(parents=True)
    mise = bin_directory / "mise"
    # A Bash-only activation catches accidental evaluation by POSIX shells.
    mise.write_text("#!/bin/sh\nprintf '%s\\n' 'mise_activation_array=(activated)'\n", encoding="utf-8")
    mise.chmod(0o700)
    environment = {key: value for key, value in os.environ.items() if key not in {"BASH_VERSION", "CLAUDECODE"}}
    environment.update(HOME=str(tmp_path), PATH=f"{bin_directory}:/usr/bin:/bin")
    command = profile + '\nprintf "login finished\\n"\n'
    if shell == "bash":
        command += 'test "${mise_activation_array[0]}" = activated\n'
    result = subprocess.run(
        [shell, "-c", command], env=environment, capture_output=True, text=True, check=False, timeout=30
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == "login finished\n"
