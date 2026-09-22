from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from typing import TypedDict, cast

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "install.sh"
# A hung bootstrap must fail its own test instead of consuming the CI job limit.
TIMEOUT_SECONDS = 60


class ToolCall(TypedDict):
    tool: str
    args: list[str]


FAKE_TOOL = """#!{python}
import json
import os
from pathlib import Path
import sys

tool = Path(sys.argv[0]).name
args = sys.argv[1:]
with Path(os.environ["BOOTSTRAP_LOG"]).open("a", encoding="utf-8") as stream:
    stream.write(json.dumps({{"tool": tool, "args": args}}) + "\\n")

if tool == "mise" and args == ["--version"]:
    print(os.environ["FAKE_MISE_VERSION"] + " fixture")
elif tool == "chezmoi" and "https://github.com/fmind/dot.git" in args:
    source = Path(args[args.index("--source") + 1])
    source.mkdir(parents=True)
elif tool == "curl" and "FAKE_MISE_STOCK" in os.environ:
    # Stand in for https://mise.run: the piped script records the requested release.
    print('printf "%s" "${{MISE_VERSION:-}}" > "$BOOTSTRAP_LOG.requested"')
    print('mkdir -p "$HOME/.local/bin" && cp "$FAKE_MISE_STOCK" "$HOME/.local/bin/mise"')
elif tool == "curl":
    raise SystemExit(99)
"""


def pinned_mise_version() -> str:
    match = re.search(r'^MINIMUM_MISE_VERSION="([0-9.]+)"$', INSTALLER.read_text(encoding="utf-8"), re.MULTILINE)
    assert match is not None
    return match.group(1)


class BootstrapFixture:
    def __init__(self, root: Path, mise_version: str, *, mise_installed: bool = True) -> None:
        self.home = root / "home"
        self.bin = root / "bin"
        self.log = root / "calls.jsonl"
        self.source = self.home / ".local" / "share" / "chezmoi"
        self.bin.mkdir(parents=True)
        stock = root / "stock"
        stock.mkdir()
        for name in ("chezmoi", "curl", "git", "mise"):
            executable = (self.bin if mise_installed or name != "mise" else stock) / name
            executable.write_text(FAKE_TOOL.format(python=sys.executable), encoding="utf-8")
            executable.chmod(0o755)
        self.environment = {
            "BOOTSTRAP_LOG": str(self.log),
            "CI": "true",
            "FAKE_MISE_VERSION": mise_version,
            "HOME": str(self.home),
            "LANG": "C.UTF-8",
            "PATH": f"{self.bin}{os.pathsep}/usr/bin{os.pathsep}/bin",
            "SKIP_GIT_PULL": "true",
        }
        if not mise_installed:
            self.environment["FAKE_MISE_STOCK"] = str(stock / "mise")

    def run(self) -> subprocess.CompletedProcess[str]:
        bash = shutil.which("bash")
        if bash is None:
            raise AssertionError("bash must be installed")
        return subprocess.run(
            [bash, str(INSTALLER)],
            env=self.environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )

    def calls(self) -> list[ToolCall]:
        if not self.log.exists():
            return []
        return [cast(ToolCall, json.loads(line)) for line in self.log.read_text(encoding="utf-8").splitlines()]


class BootstrapTest(unittest.TestCase):
    def test_unsupported_mise_fails_before_repository_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = BootstrapFixture(Path(directory), "2026.9.1")
            result = fixture.run()

            assert result.returncode != 0
            assert "mise 2026.9.10 or newer is required" in result.stderr
            assert fixture.calls() == [{"tool": "mise", "args": ["--version"]}]
            assert not fixture.source.exists()

    def test_first_install_and_rerun_use_the_bounded_task_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = BootstrapFixture(Path(directory), "2026.9.10")
            first = fixture.run()
            second = fixture.run()

            assert first.returncode == 0, first.stdout + first.stderr
            assert second.returncode == 0, second.stdout + second.stderr
            source = str(fixture.source)
            expected = [
                {"tool": "mise", "args": ["--version"]},
                {
                    "tool": "chezmoi",
                    "args": ["init", "--force", "https://github.com/fmind/dot.git", "--source", source],
                },
                {"tool": "mise", "args": ["trust", "-y", f"{source}/mise.toml"]},
                {"tool": "mise", "args": ["-C", source, "run", "install"]},
                {"tool": "mise", "args": ["--version"]},
                {"tool": "chezmoi", "args": ["init", "--force", "--source", source]},
                {"tool": "mise", "args": ["trust", "-y", f"{source}/mise.toml"]},
                {"tool": "mise", "args": ["-C", source, "run", "install"]},
            ]
            assert fixture.calls() == expected
            assert not (fixture.home / ".config" / "chezmoi" / "key.txt").exists()

    def test_missing_mise_is_installed_at_the_tested_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = BootstrapFixture(Path(directory), pinned_mise_version(), mise_installed=False)
            result = fixture.run()

            assert result.returncode == 0, result.stdout + result.stderr
            requested = Path(f"{fixture.log}.requested").read_text(encoding="utf-8")
            assert requested == f"v{pinned_mise_version()}"
            assert [call["tool"] for call in fixture.calls()[:2]] == ["curl", "mise"]

    def test_every_copy_of_the_mise_version_agrees(self) -> None:
        copies = {"install.sh": pinned_mise_version()}
        for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
            workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
            for name, job in workflow["jobs"].items():
                for step in job["steps"]:
                    if step.get("uses", "").startswith("jdx/mise-action@"):
                        # An unpinned action would install the latest mise, not the tested one.
                        copies[f"{path.name}:{name}"] = str(step.get("with", {}).get("version"))
        readme = re.search(r"requires mise ([0-9.]+[0-9])", (ROOT / "README.md").read_text(encoding="utf-8"))
        assert readme is not None
        copies["README.md"] = readme.group(1)

        assert len(copies) >= 5
        assert set(copies.values()) == {pinned_mise_version()}, copies


# Run the real mise task graph and chezmoi hooks in an empty home. Only installation
# and bat are substitutes: no vendor downloads or writes to the real workstation.
TASK_TOOL = r"""#!{python}
import os
from pathlib import Path
import sys

home = Path.home()
tool = Path(sys.argv[0]).name
args = sys.argv[1:]
def record(event):
    with Path(os.environ["TASK_LOG"]).open("a") as stream:
        stream.write(event + "\n")

if tool == "mise":
    if "install" in args and "--locked" in args:
        if "-C" in args:
            record("global-install")
            if os.environ.get("FAIL_STEP") == "global-install":
                raise SystemExit(42)
            bat = home / ".local/share/mise/shims/bat"
            bat.parent.mkdir(parents=True, exist_ok=True)
            if not bat.exists():
                bat.symlink_to(__file__)
        else:
            record("repository-install")
        raise SystemExit(0)
    os.execv(os.environ["REAL_MISE"], [os.environ["REAL_MISE"], *args])
elif tool == "chezmoi":
    record("seed" if "scripts" in args else "apply")
    os.execv(os.environ["REAL_CHEZMOI"], [os.environ["REAL_CHEZMOI"],
        "--source", os.environ["TASK_SOURCE"], "--destination", str(home),
        "--config", os.environ["TASK_CONFIG"],
        "--persistent-state", str(home / "chezmoi-state.boltdb"), *args])
elif tool == "bat":
    cache = home / ".cache/bat"
    if args == ["--cache-dir"]:
        print(cache)
    elif args == ["--version"]:
        print("bat fixture")
    elif args == ["cache", "--build"]:
        cache.mkdir(parents=True, exist_ok=True)
        record("theme-cache")
    else:
        raise SystemExit(43)
elif tool == "dot":
    record("dot " + " ".join(args))
    if args != ["completion"]:
        sys.path.insert(0, os.environ["DOT_SOURCE"])
        from fmind_dot.cli import main
        main()
elif args == ["deploy"]:
    record("deploy")
    if os.environ.get("FAIL_STEP") == "deploy":
        raise SystemExit(42)
    dot = home / ".local/share/fmind-dot/current/bin/dot"
    dot.parent.mkdir(parents=True, exist_ok=True)
    dot.unlink(missing_ok=True)
    dot.symlink_to(__file__)
else:
    record(" ".join(args))
"""


def run_task_bootstrap(
    root: Path, task: str, *, old_dot: bool = False, fail_step: str = "", repeat: bool = False
) -> tuple[subprocess.CompletedProcess[str], Path, list[str]]:
    home = root / "home with spaces"
    source = home / "source"
    source.mkdir(parents=True)
    bin_directory = root / "bin"
    bin_directory.mkdir()
    tool = bin_directory / "fixture-tool"
    tool.write_text(TASK_TOOL.replace("{python}", sys.executable))
    tool.chmod(0o755)
    for name in ("mise", "chezmoi"):
        (bin_directory / name).symlink_to(tool)
    config = tomllib.loads((ROOT / "mise.toml").read_text())
    # Keep task bodies and environment from the repository, but install no real
    # tools. The deployment implementation has separate locked-wheel tests.
    lines = ["[settings.task]", "run_auto_install = false", "[task_config]", 'dir = "{{config_root}}"', "[env]"]
    lines.extend(f"{key} = {json.dumps(value)}" for key, value in config["env"].items())
    for name in ("tools", "full", "install", "apply", "completions"):
        lines.append(f"[tasks.{name}]")
        lines.extend(f"{key} = {json.dumps(value)}" for key, value in config["tasks"][name].items())
    for name in ("deploy", "hooks", "vim"):
        lines.extend((f"[tasks.{name}]", f'run = "fixture-tool {name}"'))
    (source / "mise.toml").write_text("\n".join(lines))
    (source / ".chezmoiignore").write_text("mise.toml\n")
    (source / "dot_config/mise").mkdir(parents=True)
    (source / "dot_config/mise/config.toml").write_text("[tools]\n")
    (source / "dot_codex").mkdir()
    (source / "dot_codex/config.toml").write_text('model = "fixture"\n')
    (source / "dot_config/bat/themes").mkdir(parents=True)
    (source / "dot_config/bat/themes/fmind.tmTheme").write_text("fixture theme\n")
    (source / "dot_local/bin").mkdir(parents=True)
    shutil.copyfile(ROOT / "dot_local/bin/symlink_dot.tmpl", source / "dot_local/bin/symlink_dot.tmpl")
    for name in ("run_after_dot-trust.sh.tmpl", "run_after_bat-theme.sh.tmpl"):
        shutil.copyfile(ROOT / name, source / name)
    if old_dot:
        installed = home / ".local/share/fmind-dot/current/bin/dot"
        installed.parent.mkdir(parents=True)
        installed.write_text('#!/bin/sh\necho "old dot has no trust command" >&2\nexit 99\n')
        installed.chmod(0o755)
        (home / ".local/bin").mkdir(parents=True)
        (home / ".local/bin/dot").symlink_to(installed)
    chezmoi_config = root / "chezmoi.toml"
    chezmoi_config.write_text("")
    real_mise, real_chezmoi = shutil.which("mise"), shutil.which("chezmoi")
    assert real_mise
    assert real_chezmoi
    log = root / "events"
    environment = {
        "HOME": str(home),
        "PATH": f"{bin_directory}{os.pathsep}/usr/bin{os.pathsep}/bin",
        "MISE_TRUSTED_CONFIG_PATHS": str(home),
        "MISE_DATA_DIR": str(root / "mise-data"),
        "REAL_MISE": real_mise,
        "REAL_CHEZMOI": real_chezmoi,
        "TASK_SOURCE": str(source),
        "TASK_CONFIG": str(chezmoi_config),
        "TASK_LOG": str(log),
        "DOT_SOURCE": str(ROOT / "dot/src"),
        "FAIL_STEP": fail_step,
    }
    result = subprocess.run(
        [real_mise, "-C", str(source), "run", task],
        env=environment,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )
    if repeat:
        assert result.returncode == 0, result.stdout + result.stderr
        result = subprocess.run(
            [real_mise, "-C", str(source), "run", task],
            env=environment,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    return result, home, log.read_text().splitlines() if log.exists() else []


@pytest.mark.parametrize("task", ["tools", "full", "mf", "install"])
@pytest.mark.parametrize("old_dot", [False, True], ids=["fresh", "older-dot"])
def test_bootstrap_finishes_trust_and_theme_in_one_run(tmp_path: Path, task: str, old_dot: bool) -> None:
    result, home, events = run_task_bootstrap(tmp_path, task, old_dot=old_dot)

    assert result.returncode == 0, result.stdout + result.stderr
    assert events[:5] == ["repository-install", "seed", "global-install", "deploy", "apply"]
    assert events[5:9] == ["theme-cache", "dot trust all", f"dot trust {home / 'source'}", "dot completion"]
    assert events[9:] == (["hooks", "vim"] if task == "install" else [])
    codex = tomllib.loads((home / ".codex/config.toml").read_text())
    assert codex["projects"][str(home / "source")]["trust_level"] == "trusted"
    assert (home / ".cache/bat/fmind-theme.stamp").is_file()


@pytest.mark.parametrize("fail_step", ["global-install", "deploy"])
def test_bootstrap_failure_does_not_run_hooks_or_completions(tmp_path: Path, fail_step: str) -> None:
    result, home, events = run_task_bootstrap(tmp_path, "full", old_dot=True, fail_step=fail_step)

    assert result.returncode != 0
    assert events[-1] == fail_step
    assert "apply" not in events
    assert not any(event.startswith("dot ") for event in events)
    assert not (home / ".cache/bat/fmind-theme.stamp").exists()


def test_full_can_be_rerun_without_rebuilding_unchanged_theme(tmp_path: Path) -> None:
    result, home, events = run_task_bootstrap(tmp_path, "full", repeat=True)

    assert result.returncode == 0, result.stdout + result.stderr
    assert events.count("theme-cache") == 1
    assert events.count("dot completion") == 2
    codex = tomllib.loads((home / ".codex/config.toml").read_text())
    assert codex["projects"] == {str(home / "source"): {"trust_level": "trusted"}}
