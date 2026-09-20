"""Exercise generated task scopes and shell-free argument forwarding."""

import json
import os
import re
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


def task_closure(tasks: dict[str, dict[str, object]], name: str) -> set[str]:
    """Every task reachable through depends or a nested `mise run`, including the task itself."""
    seen: set[str] = set()
    pending = [name]
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        task = tasks[current]
        run = task.get("run", [])
        commands = [run] if isinstance(run, str) else run
        assert isinstance(commands, list)
        nested = [command.split()[2] for command in commands if str(command).startswith("mise run ")]
        depends = task.get("depends", [])
        assert isinstance(depends, list)
        pending.extend([*depends, *nested])
    return seen


def hook_tasks(hook: str) -> list[str]:
    commands = yaml.safe_load((ROOT / "lefthook.yml").read_text())[hook]["commands"]
    return [command["run"].split()[2] for command in commands.values()]


@pytest.mark.parametrize("starter", STARTERS)
def test_secret_scopes_before_and_after_first_commit(tmp_path: Path, starter: str) -> None:
    env = materialize(tmp_path, starter)
    env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})
    assert run(tmp_path, env, "git", "init", "-q").returncode == 0
    (tmp_path / ".gitleaks.toml").write_text(
        '[[rules]]\nid = "fixture"\ndescription = "Synthetic fixture"\nregex = "fixture-credential-[0-9]+"\n'
    )
    assert run(tmp_path, env, "mise", "run", "check:leaks").returncode == 0
    secret = tmp_path / "untracked.txt"
    secret.write_text("fixture-credential-12345\n")
    assert run(tmp_path, env, "mise", "run", "check:leaks").returncode != 0
    assert run(tmp_path, env, "mise", "run", "check:leaks:history").returncode == 0
    assert run(tmp_path, env, "mise", "run", "check:leaks:staged").returncode == 0
    assert run(tmp_path, env, "git", "add", "untracked.txt").returncode == 0
    staged = run(tmp_path, env, "mise", "run", "check:leaks:staged")
    assert staged.returncode != 0
    assert "fixture-credential-12345" not in staged.stdout + staged.stderr
    assert (
        run(
            tmp_path,
            env,
            "git",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ).returncode
        == 0
    )
    secret.write_text("clean\n")
    assert run(tmp_path, env, "mise", "run", "check:leaks:tree").returncode == 0
    assert run(tmp_path, env, "mise", "run", "check:leaks:history", "--no-banner").returncode != 0
    # A display flag must retain the 100-commit bound.
    for number in range(100):
        assert (
            run(
                tmp_path,
                env,
                "git",
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "--allow-empty",
                "-qm",
                str(number),
            ).returncode
            == 0
        )
    assert run(tmp_path, env, "mise", "run", "check:leaks:history", "--no-banner").returncode == 0


def test_python_staged_formatters_preserve_file_arguments(tmp_path: Path) -> None:
    env = materialize(tmp_path, "python-stack")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    ruff = ROOT / "dot/.venv/bin/ruff"
    assert ruff.is_file()
    uv = bin_dir / "uv"
    uv.write_text(
        "#!/usr/bin/env python3\nimport os, sys\n"
        'os.execv(os.environ["RUFF_BIN"], [os.environ["RUFF_BIN"], *sys.argv[3:]])\n'
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


def test_hooks_split_offline_and_network_checks_without_weakening_the_gate() -> None:
    tasks = tomllib.loads((ROOT / "mise.toml").read_text())["tasks"]
    network = {"check:scan", "check:vuln"}
    pre_commit = set().union(*(task_closure(tasks, task) for task in hook_tasks("pre-commit")))
    pre_push = set().union(*(task_closure(tasks, task) for task in hook_tasks("pre-push")))
    gate = task_closure(tasks, "all")
    checks = {name for name in tasks if name.startswith("check:")}
    # Host-dependent or credentialed audits are documented as separate from the gate.
    outside_gate = {"check:actions:online", "check:completions", "check:leaks:staged", "check:vuln:tools"}

    assert not network & pre_commit
    assert network <= pre_push
    assert "test" in pre_push
    assert checks - outside_gate <= gate
    assert checks - outside_gate - network <= pre_commit | {"check:network"}


def test_pre_commit_rejects_a_stale_skill_index_instead_of_regenerating_it() -> None:
    tasks = tomllib.loads((ROOT / "mise.toml").read_text())["tasks"]
    pre_commit = set().union(*(task_closure(tasks, task) for task in hook_tasks("pre-commit")))

    # stage_fixed restages only staged files, so a generator in this hook would leave
    # its output out of the commit and CI's clean-tree verification would fail later.
    assert "format:skills" not in pre_commit
    assert "check:skills" in pre_commit
    # The complete formatter still generates indexes before dprint formats them.
    assert {"format:skills", "format:dprint"} <= task_closure(tasks, "format")
    assert tasks["format:dprint"]["wait_for"] == ["format:skills"]


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


def test_task_examples_do_not_wrap_shells() -> None:
    paths = [ROOT / "mise.toml", *ROOT.glob("skills/**/*mise.toml"), *ROOT.glob("skills/**/*.md")]
    for path in paths:
        content = path.read_text()
        snippets = [content] if path.suffix == ".toml" else re.findall(r"```toml\n(.*?)```", content, re.DOTALL)
        for snippet in snippets:
            assert not re.search(r"\b(?:bash|sh)\s+-[^\s'\"]*c\b", snippet), path


def test_workflow_shell_steps_remain_short() -> None:
    paths = [
        *ROOT.glob(".github/workflows/*.yml"),
        *ROOT.glob("skills/github-actions/references/ci-cd/templates/*.yml"),
        ROOT / "skills/cloud-run/templates/deploy.yml",
    ]
    for path in paths:
        workflow = yaml.safe_load(path.read_text())
        for job in workflow["jobs"].values():
            for step in job.get("steps", []):
                command = step.get("run", "")
                lines = [line for line in command.splitlines() if line.strip() and not line.lstrip().startswith("#")]
                assert len(lines) <= 5, (path, step.get("name"))
                assert not re.search(r"\b(?:bash|sh)\s+-[^\s'\"]*c\b", command), path
