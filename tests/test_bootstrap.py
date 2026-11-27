from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import TypedDict, cast

import pytest
import yaml

from repo_helpers import ACTIONS, ROOT, WORKFLOWS

INSTALLER = ROOT / "install.sh"
# A hung bootstrap must fail its own test instead of consuming the CI job limit.
TIMEOUT_SECONDS = 60


class ToolCall(TypedDict):
    tool: str
    args: list[str]
    ignored_mise: str | None


FAKE_TOOL = """#!{python}
import json
import os
from pathlib import Path
import sys

tool = Path(sys.argv[0]).name
args = sys.argv[1:]
with Path(os.environ["BOOTSTRAP_LOG"]).open("a", encoding="utf-8") as stream:
    stream.write(json.dumps({{"tool": tool, "args": args, "ignored_mise": os.environ.get("MISE_IGNORED_CONFIG_PATHS")}}) + "\\n")

if tool == "git" and args[:2] == ["clone", "https://github.com/fmind/dot.git"]:
    Path(args[2]).mkdir(parents=True)
elif tool == "mise" and "which" in args and args[-1] == "chezmoi":
    print(os.environ["FAKE_CHEZMOI_BIN"])
elif tool == "curl" and "FAKE_MISE_STOCK" in os.environ:
    # Stand in for https://mise.run, including an interrupted transfer of valid shell.
    if os.environ.get("FAKE_MISE_TRUNCATED"):
        script = 'touch "$BOOTSTRAP_LOG.executed"\\n'
    else:
        script = 'printf "%s" "${{MISE_VERSION:-}}" > "$BOOTSTRAP_LOG.requested"\\n'
        script += 'mkdir -p "$HOME/.local/bin" && cp "$FAKE_MISE_STOCK" "$HOME/.local/bin/mise"\\n'
    if "-o" in args:
        Path(args[args.index("-o") + 1]).write_text(script)
    else:
        print(script)
    if os.environ.get("FAKE_MISE_TRUNCATED"):
        raise SystemExit(18)
elif tool == "curl":
    raise SystemExit(99)
"""


def pinned_mise_version() -> str:
    match = re.search(r'^MINIMUM_MISE_VERSION="([0-9.]+)"$', INSTALLER.read_text(encoding="utf-8"), re.MULTILINE)
    assert match is not None
    return match.group(1)


class BootstrapFixture:
    def __init__(self, root: Path, *, mise_installed: bool = True, chezmoi_installed: bool = True) -> None:
        self.home = root / "home"
        self.bin = root / "bin"
        self.log = root / "calls.jsonl"
        self.source = self.home / ".local" / "share" / "chezmoi"
        self.bin.mkdir(parents=True)
        stock = root / "stock"
        stock.mkdir()
        for name in ("chezmoi", "curl", "git", "mise"):
            in_bin = (mise_installed or name != "mise") and (chezmoi_installed or name != "chezmoi")
            executable = (self.bin if in_bin else stock) / name
            executable.write_text(FAKE_TOOL.format(python=sys.executable), encoding="utf-8")
            executable.chmod(0o755)
        self.environment = {
            "BOOTSTRAP_LOG": str(self.log),
            "HOME": str(self.home),
            "LANG": "C.UTF-8",
            "PATH": f"{self.bin}{os.pathsep}/usr/bin{os.pathsep}/bin",
            "SKIP_GIT_PULL": "true",
        }
        if not mise_installed:
            self.environment["FAKE_MISE_STOCK"] = str(stock / "mise")
        if not chezmoi_installed:
            self.environment["FAKE_CHEZMOI_BIN"] = str(stock / "chezmoi")

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


def test_first_install_and_rerun_use_the_bounded_task_sequence(tmp_path: Path) -> None:
    fixture = BootstrapFixture(tmp_path)
    first = fixture.run()
    second = fixture.run()

    assert first.returncode == 0, first.stdout + first.stderr
    assert second.returncode == 0, second.stdout + second.stderr
    source = str(fixture.source)
    expected = [
        {"tool": "git", "args": ["clone", "https://github.com/fmind/dot.git", source]},
        {"tool": "mise", "args": ["trust", "-y", f"{source}/mise.toml"]},
        {"tool": "chezmoi", "args": ["init", "--force", "--source", source]},
        {"tool": "mise", "args": ["-C", source, "run", "install"]},
        {"tool": "mise", "args": ["trust", "-y", f"{source}/mise.toml"]},
        {"tool": "chezmoi", "args": ["init", "--force", "--source", source]},
        {"tool": "mise", "args": ["-C", source, "run", "install"]},
    ]
    assert [(c["tool"], c["args"]) for c in fixture.calls()] == [(c["tool"], c["args"]) for c in expected]
    assert not (fixture.home / ".config" / "chezmoi" / "key.txt").exists()

    # Rerun with SKIP_GIT_PULL unset fast-forwards the existing repository.
    fixture.environment.pop("SKIP_GIT_PULL", None)
    fixture.log.unlink()
    third = fixture.run()
    assert third.returncode == 0, third.stdout + third.stderr
    assert [(c["tool"], c["args"]) for c in fixture.calls()] == [
        ("git", ["-C", source, "pull", "--ff-only"]),
        ("mise", ["trust", "-y", f"{source}/mise.toml"]),
        ("chezmoi", ["init", "--force", "--source", source]),
        ("mise", ["-C", source, "run", "install"]),
    ]


def test_missing_chezmoi_uses_locked_repository_install(tmp_path: Path) -> None:
    fixture = BootstrapFixture(tmp_path, chezmoi_installed=False)
    result = fixture.run()

    assert result.returncode == 0, result.stdout + result.stderr
    source = str(fixture.source)
    ignored = str(fixture.home / ".config" / "mise")
    assert fixture.calls() == [
        {"tool": "git", "args": ["clone", "https://github.com/fmind/dot.git", source], "ignored_mise": None},
        {"tool": "mise", "args": ["trust", "-y", f"{source}/mise.toml"], "ignored_mise": None},
        {
            "tool": "mise",
            "args": ["-C", source, "--locked", "install", "-y", "chezmoi"],
            "ignored_mise": ignored,
        },
        {"tool": "mise", "args": ["-C", source, "which", "chezmoi"], "ignored_mise": ignored},
        {"tool": "chezmoi", "args": ["init", "--force", "--source", source], "ignored_mise": None},
        {"tool": "mise", "args": ["-C", source, "run", "install"], "ignored_mise": None},
    ]


def test_missing_mise_is_installed_at_the_tested_version(tmp_path: Path) -> None:
    fixture = BootstrapFixture(tmp_path, mise_installed=False)
    result = fixture.run()

    assert result.returncode == 0, result.stdout + result.stderr
    requested = Path(f"{fixture.log}.requested").read_text(encoding="utf-8")
    assert requested == f"v{pinned_mise_version()}"
    assert [call["tool"] for call in fixture.calls()[:2]] == ["curl", "git"]


def test_interrupted_mise_download_is_never_executed(tmp_path: Path) -> None:
    fixture = BootstrapFixture(tmp_path, mise_installed=False)
    fixture.environment["FAKE_MISE_TRUNCATED"] = "1"
    result = fixture.run()

    assert result.returncode == 18, result.stdout + result.stderr
    assert not Path(f"{fixture.log}.executed").exists()
    assert not fixture.source.exists()
    (download,) = fixture.calls()
    assert download["tool"] == "curl"
    assert not Path(download["args"][download["args"].index("-o") + 1]).exists()


def test_every_copy_of_the_mise_version_agrees() -> None:
    copies = {"install.sh": pinned_mise_version()}
    # Shipped workflow and composite-action templates scaffold other repositories with the same tested mise.
    for path in WORKFLOWS:
        workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
        for name, job in workflow["jobs"].items():
            for index, step in enumerate(job.get("steps", [])):
                if step.get("uses", "").startswith("jdx/mise-action@"):
                    # An unpinned action would install the latest mise, not the tested one.
                    relative = path.relative_to(ROOT)
                    copies[f"{relative}:{name}:{index}"] = str(step.get("with", {}).get("version"))
    for path in ACTIONS:
        action = yaml.safe_load(path.read_text(encoding="utf-8"))
        for index, step in enumerate(action.get("runs", {}).get("steps", [])):
            if step.get("uses", "").startswith("jdx/mise-action@"):
                relative = path.relative_to(ROOT)
                copies[f"{relative}:runs:{index}"] = str(step.get("with", {}).get("version"))
    for template in (
        "skills/python/references/foundation/templates",
        "skills/infra-as-code/templates",
        "skills/docs/references/site/templates",
    ):
        config = tomllib.loads((ROOT / template / "mise.toml").read_text(encoding="utf-8"))
        copies[f"{template}/mise.toml"] = str(config.get("min_version"))
        settings = config.get("settings", {})
        assert settings.get("lockfile") is True, template
        assert settings.get("lockfile_platforms") == ["linux-arm64", "linux-x64", "macos-arm64"], template
        assert settings.get("minimum_release_age") == "0d", template
    readme = re.search(r"requires mise ([0-9.]+[0-9])", (ROOT / "README.md").read_text(encoding="utf-8"))
    assert readme is not None
    copies["README.md"] = readme.group(1)
    copies["mise.toml"] = str(tomllib.loads((ROOT / "mise.toml").read_text(encoding="utf-8")).get("min_version"))

    assert len(copies) >= 12
    assert set(copies.values()) == {pinned_mise_version()}, copies


def test_dprint_template_plugins_and_dockerfile_pins_match_repo_locks() -> None:
    def load_jsonc(path: Path) -> dict[str, object]:
        return cast(dict[str, object], json.loads(re.sub(r"(?m)^\s*//.*$", "", path.read_text(encoding="utf-8"))))

    assert (
        load_jsonc(ROOT / "skills/mise/templates/dprint.json")["plugins"] == load_jsonc(ROOT / "dprint.json")["plugins"]
    )

    lock = tomllib.loads((ROOT / "mise.lock").read_text(encoding="utf-8"))["tools"]
    python_version = lock["python"][0]["version"]
    uv_version = lock["uv"][0]["version"]
    dockerfile = (ROOT / "skills/containers/references/containerize/templates/Dockerfile").read_text(encoding="utf-8")
    assert f"FROM python:{python_version}-slim@sha256:" in dockerfile
    assert f"COPY --from=ghcr.io/astral-sh/uv:{uv_version}@sha256:" in dockerfile


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
elif tool == "uv" and "dot_tasks.mise_locks" in args:
    record("retire " + args[-1].removeprefix(str(home)))
elif tool == "uv" and "dot_tasks.completions" in args:
    record("completions")
elif tool == "dot":
    record("dot " + " ".join(args))
    sys.path.insert(0, os.environ["DOT_SOURCE"])
    from fmind_dot.cli import main
    main()
elif tool == "lefthook":
    record("hooks")
elif args == ["deploy"]:
    record("deploy")
    if os.environ.get("FAIL_STEP") == "deploy":
        raise SystemExit(42)
    dot = home / ".local/bin/dot"
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
    for name in ("mise", "chezmoi", "uv", "lefthook"):
        (bin_directory / name).symlink_to(tool)
    config = tomllib.loads((ROOT / "mise.toml").read_text())
    # Keep task bodies, variables, and environment from the repository, but install no
    # real tools; the deploy fixture stands in for uv tool install.
    lines = ["[settings.task]", "run_auto_install = false"]
    for section in ("env", "vars"):
        lines.append(f"[{section}]")
        lines.extend(f"{key} = {json.dumps(value)}" for key, value in config[section].items())
    for name in ("full", "install", "apply", "completions"):
        lines.append(f"[tasks.{name}]")
        lines.extend(f"{key} = {json.dumps(value)}" for key, value in config["tasks"][name].items())
    for name in ("deploy", "vim"):
        lines.extend((f"[tasks.{name}]", f'run = "fixture-tool {name}"'))
    (source / "mise.toml").write_text("\n".join(lines))
    (source / ".chezmoiignore").write_text("mise.toml\n")
    (source / "dot_config/mise").mkdir(parents=True)
    (source / "dot_config/mise/config.toml").write_text("[tools]\n")
    # Antigravity state gives the trust hook a harness file to extend.
    (source / "private_dot_gemini/private_antigravity-cli").mkdir(parents=True)
    (source / "private_dot_gemini/private_antigravity-cli/settings.json").write_text('{"editorMode": "vim"}\n')
    (source / "dot_config/bat/themes").mkdir(parents=True)
    (source / "dot_config/bat/themes/fmind.tmTheme").write_text("fixture theme\n")
    for name in ("run_after_dot-trust.sh.tmpl", "run_after_bat-theme.sh.tmpl"):
        shutil.copyfile(ROOT / name, source / name)
    if old_dot:
        installed = home / ".local/bin/dot"
        installed.parent.mkdir(parents=True)
        installed.write_text('#!/bin/sh\necho "old dot has no trust command" >&2\nexit 99\n')
        installed.chmod(0o755)
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


@pytest.mark.parametrize("task", ["full", "install"])
@pytest.mark.parametrize("old_dot", [False, True], ids=["fresh", "older-dot"])
def test_bootstrap_finishes_trust_and_theme_in_one_run(tmp_path: Path, task: str, old_dot: bool) -> None:
    result, home, events = run_task_bootstrap(tmp_path, task, old_dot=old_dot)

    assert result.returncode == 0, result.stdout + result.stderr
    # Retiring runs before the global install, which rebuilds any install it removed.
    assert events[:6] == [
        "repository-install",
        "seed",
        "retire /.config/mise/mise.lock",
        "global-install",
        "deploy",
        "apply",
    ]
    assert events[6:9] == ["theme-cache", f"dot trust all {home / 'source'}", "completions"]
    assert events[9:] == (["hooks", "vim"] if task == "install" else [])
    agy = json.loads((home / ".gemini/antigravity-cli/settings.json").read_text())
    assert agy["trustedWorkspaces"] == [str(home / "source")]
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
    assert events.count("completions") == 2
    agy = json.loads((home / ".gemini/antigravity-cli/settings.json").read_text())
    assert agy == {"editorMode": "vim", "trustedWorkspaces": [str(home / "source")]}


def test_repository_install_can_repair_a_broken_global_tool_config(tmp_path: Path) -> None:
    mise = shutil.which("mise")
    assert mise is not None
    source = tmp_path / "repository"
    source.mkdir()
    global_config = tmp_path / "global"
    global_config.mkdir()
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (global_config / "config.toml").write_text(f'[tools]\n"pypi:fixture" = "path:{runtime}"\n')
    config = tomllib.loads((ROOT / "mise.toml").read_text())
    task = config["tasks"]["full"]["run"][0]
    # The real first bootstrap step must ignore a home tool that cannot satisfy
    # --locked. No repository tools are needed for this isolated selection probe.
    (source / "mise.toml").write_text(
        f"[vars]\nrepo_mise = {json.dumps(config['vars']['repo_mise'])}\n"
        f"[settings.task]\nrun_auto_install = false\n[tasks.probe]\nrun = {json.dumps(task)}\n"
    )
    result = subprocess.run(
        [mise, "-C", str(source), "run", "probe"],
        env={
            "HOME": str(tmp_path),
            "PATH": str(Path(mise).parent) + os.pathsep + os.defpath,
            "MISE_CONFIG_DIR": str(global_config),
            "MISE_TRUSTED_CONFIG_PATHS": str(source),
            "MISE_OFFLINE": "1",
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=TIMEOUT_SECONDS,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (tmp_path / ".local/share/mise/installs").exists()


def test_ci_workflow_keeps_full_history_for_skill_freshness_and_checks_completions() -> None:
    ci = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    steps = ci["jobs"]["ci"]["steps"]
    checkout = next(step for step in steps if step.get("uses", "").startswith("actions/checkout@"))
    depth = checkout.get("with", {}).get("fetch-depth")
    assert type(depth) is int
    assert depth == 0
    assert any(
        "if" not in step
        and not step.get("continue-on-error")
        and any(line.strip() == "mise run check:completions" for line in str(step.get("run", "")).splitlines())
        for step in steps
    )
