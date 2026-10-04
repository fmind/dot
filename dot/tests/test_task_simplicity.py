"""Exercise generated task scopes and shell-free argument forwarding."""

import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
STARTERS = {
    "python-stack": "skills/python-stack/references/foundation/templates/mise.toml",
    "terraform": "skills/infra-as-code/templates/mise.toml",
}
# A hung task must fail its own test instead of consuming the CI job limit.
TIMEOUT_SECONDS = 120


def materialize(root: Path, starter: str, prefix: str = "") -> dict[str, str]:
    config = tomllib.loads((ROOT / STARTERS.get(starter, starter)).read_text())
    lines = ["[settings.task]", "run_auto_install = false"]
    for name, task in config["tasks"].items():
        if not name.startswith(prefix):
            continue
        lines.append(f"[tasks.{json.dumps(name)}]")
        lines.extend(f"{key} = {json.dumps(value)}" for key, value in task.items())
    (root / "mise.toml").write_text("\n".join(lines))
    mise = shutil.which("mise")
    assert mise is not None
    gitleaks = subprocess.check_output([mise, "which", "gitleaks"], cwd=ROOT, text=True, timeout=60).strip()
    return {
        "PATH": os.pathsep.join(
            [str(Path(mise).parent), str(Path(gitleaks).parent), str(Path(sys.executable).parent), os.defpath]
        ),
        "HOME": str(root),
        "MISE_CONFIG_DIR": str(root / "config"),
        "MISE_TRUSTED_CONFIG_PATHS": str(root),
    }


def run(root: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=root, env=env, capture_output=True, text=True, check=False, timeout=TIMEOUT_SECONDS)


@pytest.mark.parametrize("starter", STARTERS)
def test_secret_scan_covers_untracked_files(tmp_path: Path, starter: str) -> None:
    env = materialize(tmp_path, starter)
    env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})
    assert run(tmp_path, env, "git", "init", "-q").returncode == 0
    (tmp_path / ".gitleaks.toml").write_text(
        '[[rules]]\nid = "fixture"\ndescription = "Synthetic fixture"\nregex = "fixture-credential-[0-9]+"\n'
    )
    assert run(tmp_path, env, "mise", "run", "check:leaks").returncode == 0
    secret = tmp_path / "untracked.txt"
    secret.write_text("fixture-credential-12345\n")
    untracked = run(tmp_path, env, "mise", "run", "check:leaks")
    assert untracked.returncode != 0
    assert "fixture-credential-12345" not in untracked.stdout + untracked.stderr


def test_python_staged_formatters_preserve_file_arguments(tmp_path: Path) -> None:
    env = materialize(tmp_path, "python-stack")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    ruff = ROOT / "dot/.venv/bin/ruff"
    assert ruff.is_file()
    uv = bin_dir / "uv"
    uv.write_text(
        "#!/usr/bin/env python3\nimport os, sys\n"
        'os.execv(os.environ["RUFF_BIN"], [os.environ["RUFF_BIN"], *sys.argv[sys.argv.index("ruff") + 1 :]])\n'
    )
    uv.chmod(0o755)
    env.update({"PATH": f"{bin_dir}:{env['PATH']}", "RUFF_BIN": str(ruff)})
    selected = tmp_path / "chosen space ' ; $(touch injected).py"
    unrelated = tmp_path / "unrelated.py"
    text = "import sys\nimport os\nx=1\n"
    selected.write_text(text)
    unrelated.write_text(text)
    hooks = yaml.safe_load((ROOT / "skills/python-stack/references/foundation/templates/lefthook.yml").read_text())[
        "pre-commit"
    ]["commands"]
    formatters = sorted(
        (hook for name, hook in hooks.items() if name.startswith("format:") and hook["glob"] == "*.py"),
        key=lambda hook: hook["priority"],
    )
    for hook in formatters:
        task = hook["run"].split()[2]
        result = run(tmp_path, env, "mise", "run", task, selected.name)
        assert result.returncode == 0, result.stderr
    assert selected.read_text() == "import os\nimport sys\n\nx = 1\n"
    assert unrelated.read_text() == text
    assert not (tmp_path / "injected").exists()
    selected.write_text("invalid (\n")
    assert run(tmp_path, env, "mise", "run", "format:python").returncode != 0


def test_repository_python_hooks_format_only_staged_files(tmp_path: Path) -> None:
    env = materialize(tmp_path, "mise.toml", prefix="format:python:")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    ruff = ROOT / "dot/.venv/bin/ruff"
    assert ruff.is_file()
    uv = bin_dir / "uv"
    uv.write_text(
        "#!/usr/bin/env python3\nimport os, sys\n"
        'os.execv(os.environ["RUFF_BIN"], [os.environ["RUFF_BIN"], *sys.argv[sys.argv.index("ruff") + 1 :]])\n'
    )
    uv.chmod(0o755)
    env.update({"PATH": f"{bin_dir}:{env['PATH']}", "RUFF_BIN": str(ruff)})
    selected = tmp_path / "chosen space ' ; $(touch injected).py"
    unrelated = tmp_path / "unrelated.py"
    text = "import os\nx=1\n"
    selected.write_text(text)
    unrelated.write_text(text)
    hooks = yaml.safe_load((ROOT / "lefthook.yml").read_text())["pre-commit"]["commands"]
    formatters = sorted(
        (hook for hook in hooks.values() if "**/*.py" in hook.get("glob", "")), key=lambda hook: hook["priority"]
    )
    assert formatters
    for hook in formatters:
        assert hook["run"].endswith(" {staged_files}")
        assert hook["stage_fixed"] is True
        result = run(tmp_path, env, "mise", "run", hook["run"].split()[2], selected.name)
        assert result.returncode == 0, result.stderr
    # Ruff's defaults apply in the fixture: the fix task drops the unused import, the style task reflows.
    assert selected.read_text() == "x = 1\n"
    assert unrelated.read_text() == text
    assert not (tmp_path / "injected").exists()


def test_repository_lua_hook_preserves_unselected_files(tmp_path: Path) -> None:
    env = materialize(tmp_path, "mise.toml", prefix="format:lua")
    stylua = subprocess.check_output(["mise", "which", "stylua"], cwd=ROOT, text=True, timeout=60).strip()
    env["PATH"] = f"{Path(stylua).parent}:{env['PATH']}"
    directory = tmp_path / "dot_config/nvim"
    directory.mkdir(parents=True)
    selected, unrelated = directory / "selected space.lua", directory / "unrelated.lua"
    source = "local x={1,2,3}\n"
    selected.write_text(source)
    unrelated.write_text(source)
    hooks = yaml.safe_load((ROOT / "lefthook.yml").read_text())["pre-commit"]["commands"]
    [hook] = [hook for hook in hooks.values() if hook.get("glob") == "**/*.lua"]
    result = run(tmp_path, env, "mise", "run", hook["run"].split()[2], str(selected))
    assert result.returncode == 0, result.stderr
    assert selected.read_text() != source
    assert unrelated.read_text() == source
    assert run(tmp_path, env, "mise", "run", "format:lua").returncode == 0
    assert unrelated.read_text() != source


def test_terraform_formatter_forwards_files_and_failures(tmp_path: Path) -> None:
    env = materialize(tmp_path, "terraform")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    tofu = bin_dir / "tofu"
    tofu.write_text(
        "#!/usr/bin/env python3\nimport json, os, sys\nfrom pathlib import Path\n"
        'Path("args.json").write_text(json.dumps(sys.argv[1:]))\n'
        'sys.exit(int(os.environ.get("TOFU_EXIT", "0")))\n'
    )
    tofu.chmod(0o755)
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    selected = "selected space.tf"
    assert run(tmp_path, env, "mise", "run", "format:tofu", selected).returncode == 0
    assert json.loads((tmp_path / "args.json").read_text()) == ["fmt", "-recursive", selected]
    assert run(tmp_path, env, "mise", "run", "format:tofu").returncode == 0
    assert json.loads((tmp_path / "args.json").read_text()) == ["fmt", "-recursive"]
    env["TOFU_EXIT"] = "1"
    assert run(tmp_path, env, "mise", "run", "format:tofu", selected).returncode != 0
