"""Exercise the login-shell modify templates against empty, existing, and second-pass targets."""

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
