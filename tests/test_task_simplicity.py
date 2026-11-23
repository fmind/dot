"""Exercise generated task scopes and shell-free argument forwarding."""

import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
import yaml

from repo_helpers import load_script

# These tests run repository hooks through mise shims, which resolve tools from the real HOME.
pytestmark = pytest.mark.real_home

ROOT = Path(__file__).resolve().parents[1]
STARTERS = {
    "python": "skills/python/references/foundation/templates/mise.toml",
    "terraform": "skills/infra-as-code/templates/mise.toml",
    "docs": "skills/docs/references/site/templates/mise.toml",
}
DOCS_STARTERS = ("skills/docs/references/site/templates/mise.toml",)
# A hung task must fail its own test instead of consuming the CI job limit.
TIMEOUT_SECONDS = 120


def _toml_value(value: object) -> str:
    if isinstance(value, dict):
        pairs = ", ".join(f"{json.dumps(k)} = {_toml_value(v)}" for k, v in value.items())
        return "{ " + pairs + " }"
    return json.dumps(value)


def materialize(root: Path, starter: str, prefix: str = "") -> dict[str, str]:
    config = tomllib.loads((ROOT / STARTERS.get(starter, starter)).read_text())
    lines = ["[settings.task]", "run_auto_install = false", "[vars]"]
    lines.extend(f"{key} = {_toml_value(value)}" for key, value in config.get("vars", {}).items())
    for name, task in config["tasks"].items():
        if not name.startswith(prefix):
            continue
        lines.append(f"[tasks.{json.dumps(name)}]")
        lines.extend(f"{key} = {_toml_value(value)}" for key, value in task.items())
    (root / "mise.toml").write_text("\n".join(lines))
    mise = shutil.which("mise")
    assert mise is not None
    return {
        "PATH": os.pathsep.join([str(Path(mise).parent), str(Path(sys.executable).parent), os.defpath]),
        "HOME": str(root),
        "MISE_CONFIG_DIR": str(root / "config"),
        "MISE_STATE_DIR": str(root / "mise-state"),
        "MISE_TRUSTED_CONFIG_PATHS": str(root),
    }


def _route_uv_to_ruff(root: Path, env: dict[str, str]) -> None:
    """Shim `uv run ... ruff ARGS` to the locked dot venv Ruff so hooks run without network."""
    bin_dir = root / "bin"
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


def run(root: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=root, env=env, capture_output=True, text=True, check=False, timeout=TIMEOUT_SECONDS)


@pytest.mark.parametrize("starter", STARTERS)
def test_starter_task_graph_validates(tmp_path: Path, starter: str) -> None:
    # The whole template, not a task subset: mise checks every task, dependency, and setting.
    starter_path = ROOT / STARTERS[starter]
    config = tomllib.loads(starter_path.read_text(encoding="utf-8"))
    baseline_tools = {"betterleaks", "dprint", "git-cliff", "jactionlint", "lefthook", "lychee", "shellcheck", "typos"}
    assert baseline_tools <= set(config["tools"]), f"{starter} missing baseline tools"
    assert {"check:links", "check:typos"} <= set(config["tasks"]["check:local"]["depends"])
    assert (
        config["tasks"]["check:links"]["run"] == "lychee --offline --include-fragments --no-progress --extensions md ."
    )
    assert config["tasks"]["check:typos"]["run"] == "typos"
    assert config["tasks"]["check:tasks"]["run"] == ["mise tasks validate", "lefthook validate"]
    shutil.copy2(starter_path, tmp_path / "mise.toml")
    mise = shutil.which("mise")
    assert mise is not None
    env = {
        "PATH": os.pathsep.join([str(Path(mise).parent), os.defpath]),
        "HOME": str(tmp_path),
        "MISE_CONFIG_DIR": str(tmp_path / "config"),
        "MISE_STATE_DIR": str(tmp_path / "mise-state"),
        "MISE_TRUSTED_CONFIG_PATHS": str(tmp_path),
    }
    result = run(tmp_path, env, "mise", "tasks", "validate")
    assert result.returncode == 0, result.stdout + result.stderr


def test_security_policy_template_placeholders() -> None:
    security_text = (ROOT / "skills/github/templates/SECURITY.md").read_text(encoding="utf-8")
    assert "<owner>" in security_text
    assert "<slug>" in security_text
    rendered_security = security_text.replace("<owner>", "example").replace("<slug>", "demo-repo")
    assert re.findall(r"<[a-z][a-z0-9_-]*>", rendered_security) == []
    assert "https://github.com/example/demo-repo/releases/latest" in rendered_security
    assert "https://github.com/example/demo-repo/security/advisories/new" in rendered_security


def test_cliff_template_parity_and_cli(tmp_path: Path) -> None:
    cliff_template = ROOT / "skills/git-delivery/templates/cliff.toml"
    cliff_cfg = tomllib.loads(cliff_template.read_text(encoding="utf-8"))
    dot_cliff_cfg = tomllib.loads((ROOT / "dot_config/git-cliff/cliff.toml").read_text(encoding="utf-8"))
    assert cliff_cfg["changelog"] == dot_cliff_cfg["changelog"]
    assert cliff_cfg["bump"] == dot_cliff_cfg["bump"]
    assert cliff_cfg["git"]["protect_breaking_commits"] is True
    assert cliff_cfg["git"]["tag_pattern"] == dot_cliff_cfg["git"]["tag_pattern"]

    # Skill templates avoid U+FE0F variation selectors (skill_contracts), so compare messages, skip flags, and labels.
    def _group_label(parser: dict[str, object]) -> str:
        return re.sub(r"^<!-- \d+ -->\S+\s+", "", str(parser.get("group", "")))

    assert [
        (p["message"], bool(p.get("skip", False)), _group_label(p)) for p in cliff_cfg["git"]["commit_parsers"]
    ] == [(p["message"], bool(p.get("skip", False)), _group_label(p)) for p in dot_cliff_cfg["git"]["commit_parsers"]]

    git_cliff = subprocess.check_output(["mise", "which", "git-cliff"], cwd=ROOT, text=True, timeout=60).strip()
    env = {
        "PATH": os.pathsep.join([str(Path(git_cliff).parent), os.defpath]),
        "HOME": str(tmp_path),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_AUTHOR_NAME": "Fixture Author",
        "GIT_AUTHOR_EMAIL": "fixture@example.com",
        "GIT_COMMITTER_NAME": "Fixture Author",
        "GIT_COMMITTER_EMAIL": "fixture@example.com",
    }
    assert run(tmp_path, env, "git", "init", "-q", "-b", "main").returncode == 0
    shutil.copy2(cliff_template, tmp_path / "cliff.toml")
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# Changelog\n\nAll notable changes to this project are documented in this file.\n")
    assert run(tmp_path, env, "git", "add", "cliff.toml", "CHANGELOG.md").returncode == 0
    assert run(tmp_path, env, "git", "commit", "-q", "-m", "feat: initial release").returncode == 0
    assert run(tmp_path, env, "git", "commit", "-q", "--allow-empty", "-m", "chore(release): v0.0.0").returncode == 0

    bumped = run(tmp_path, env, git_cliff, "--bumped-version")
    assert bumped.returncode == 0, bumped.stderr
    assert bumped.stdout.strip() == "v0.1.0"

    prepend = run(tmp_path, env, git_cliff, "--unreleased", "--tag", "v0.1.0", "--prepend", "CHANGELOG.md")
    assert prepend.returncode == 0, prepend.stderr
    content = changelog.read_text(encoding="utf-8")
    assert content.count("# Changelog") == 1
    assert "## [0.1.0]" in content
    assert "- Initial release" in content
    assert "v0.0.0" not in content


def test_bdd_templates_hooks_and_sanitizer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, object]] = []

    class SeverityLevel(Enum):
        CRITICAL = "critical"
        NORMAL = "normal"

    class FakeAllure(ModuleType):
        severity_level = SeverityLevel
        dynamic = SimpleNamespace(story=lambda name: calls.append(("story", name)))

        @staticmethod
        def issue(issue_id: str) -> Callable[[Callable[[], None]], Callable[[], None]]:
            def decorate(fn: Callable[[], None]) -> Callable[[], None]:
                calls.append(("issue", issue_id))
                return fn

            return decorate

        @staticmethod
        def severity(level: SeverityLevel) -> Callable[[Callable[[], None]], Callable[[], None]]:
            def decorate(fn: Callable[[], None]) -> Callable[[], None]:
                calls.append(("severity", level))
                return fn

            return decorate

    monkeypatch.setitem(sys.modules, "allure", FakeAllure("allure"))

    conftest = load_script("bdd_conftest_tpl", ROOT / "skills/python/references/testing/templates/bdd-conftest.py")

    def marker_fn() -> None:
        return None

    assert conftest.pytest_bdd_apply_tag("issue_42", marker_fn) is True
    assert conftest.pytest_bdd_apply_tag("issue_", marker_fn) is None
    assert conftest.pytest_bdd_apply_tag("issue_bad/path", marker_fn) is None
    assert conftest.pytest_bdd_apply_tag("severity_critical", marker_fn) is True
    assert conftest.pytest_bdd_apply_tag("severity_high", marker_fn) is None
    assert conftest.pytest_bdd_apply_tag("severity_", marker_fn) is None
    assert conftest.pytest_bdd_apply_tag("sla", marker_fn) is None

    # Pluggy LIFO requires trylast=True so allure-pytest-bdd schedules the TestResult first.
    assert getattr(conftest.pytest_bdd_before_scenario, "pytest_impl", None) is not None
    assert conftest.pytest_bdd_before_scenario.pytest_impl["trylast"] is True
    conftest.pytest_bdd_before_scenario(SimpleNamespace(rule=SimpleNamespace(name="Budget rules")))
    conftest.pytest_bdd_before_scenario(SimpleNamespace(rule=None))
    assert calls == [("issue", "42"), ("severity", SeverityLevel.CRITICAL), ("story", "Budget rules")]

    wip_req = SimpleNamespace(node=SimpleNamespace(get_closest_marker=lambda name: object() if name == "wip" else None))
    with pytest.raises(pytest.skip.Exception, match="missing step"):
        conftest.pytest_bdd_step_func_lookup_error(wip_req, SimpleNamespace(name="missing step"))
    non_wip_req = SimpleNamespace(node=SimpleNamespace(get_closest_marker=lambda _name: None))
    assert conftest.pytest_bdd_step_func_lookup_error(non_wip_req, SimpleNamespace(name="missing step")) is None

    report_bdd = load_script("report_bdd_tpl", ROOT / "skills/python/references/testing/templates/report_bdd.py")
    real_home = tmp_path / "real-home"
    real_repo = real_home / "work/project"
    real_repo.mkdir(parents=True)
    link_home = tmp_path / "link-home"
    link_home.symlink_to(real_home)
    link_repo = link_home / "work/project"

    results = tmp_path / "allure-results"
    results.mkdir()
    (results / "1-result.json").write_text(
        json.dumps(
            {
                "name": "order passes",
                "labels": [{"name": "host", "value": "laptop.local"}, {"name": "tag", "value": "sla"}],
                "statusDetails": {
                    "trace": f"File '{real_repo}/src/app.py', cwd='{link_repo}', home='{real_home}' and '{link_home}/.cfg'"
                },
            }
        ),
        encoding="utf-8",
    )
    (results / "1-container.json").write_text(
        json.dumps({"name": f"setup at {real_repo} for {real_home}/bin"}), encoding="utf-8"
    )
    (results / "1-attachment.txt").write_text(
        f"stdout: {link_repo}/file.py HOME={link_home} sibling={real_repo}-other\n", encoding="utf-8"
    )
    sla_json = '{\n  "p95_ms": 42\n}\n'
    (results / "1-attachment.json").write_text(sla_json, encoding="utf-8")
    (results / "2-attachment.json").write_text("{truncated", encoding="utf-8")
    (results / "3-attachment.txt").write_bytes(b"\xff\xfe\x00binary")

    report_bdd.sanitize_results(results, cwd=link_repo, home=link_home)

    res = json.loads((results / "1-result.json").read_text(encoding="utf-8"))
    assert res["labels"] == [{"name": "tag", "value": "sla"}]
    assert res["statusDetails"]["trace"] == "File 'src/app.py', cwd='.', home='~' and '~/.cfg'"
    container = json.loads((results / "1-container.json").read_text(encoding="utf-8"))
    assert container["name"] == "setup at . for ~/bin"
    assert (results / "1-attachment.txt").read_text(encoding="utf-8") == (
        "stdout: file.py HOME=~ sibling=~/work/project-other\n"
    )
    assert (results / "1-attachment.json").read_text(encoding="utf-8") == sla_json
    assert (results / "2-attachment.json").read_text(encoding="utf-8") == "{truncated"
    assert (results / "3-attachment.txt").read_bytes() == b"\xff\xfe\x00binary"


def test_allurerc_yaml_template_structure() -> None:
    cfg = yaml.safe_load(
        (ROOT / "skills/python/references/testing/templates/allurerc.yaml").read_text(encoding="utf-8")
    )
    assert cfg["output"] == ".cache/allure-report"
    awesome = cfg["plugins"]["awesome"]["options"]
    assert awesome["singleFile"] is True
    assert awesome["groupBy"] == ["feature", "story"]
    assert len(cfg["categories"]["rules"]) >= 3
    gate = cfg["qualityGate"]["rules"][0]
    assert gate["id"] == "implemented-specs"
    assert gate["maxFailures"] == 0
    assert gate["minTestsCount"] == 1
    assert gate["filter"].strip() == "${{ !test.labels.exists(l, l.name == 'tag' && l.value == 'wip') }}"


@pytest.mark.parametrize(
    ("pytest_rc", "qg_rc", "log_rc", "expected_rc", "expect_allure"),
    [
        (0, 0, 0, 0, True),
        (1, 1, 0, 1, True),
        (0, 0, 2, 2, True),
        (2, 0, 0, 2, False),
        (-9, 0, 0, 137, False),
    ],
)
def test_report_bdd_main_orchestration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pytest_rc: int,
    qg_rc: int,
    log_rc: int,
    expected_rc: int,
    expect_allure: bool,
) -> None:
    report_bdd = load_script("report_bdd_main_tpl", ROOT / "skills/python/references/testing/templates/report_bdd.py")
    monkeypatch.chdir(tmp_path)
    events: list[str] = []

    def fake_run(cmd: list[str], *, check: bool = False) -> SimpleNamespace:
        assert check is False
        if cmd[0] == "uv":
            events.append("pytest")
            results_dir = tmp_path / ".cache/allure-results"
            results_dir.mkdir(parents=True, exist_ok=True)
            (results_dir / "1-result.json").write_text(
                json.dumps({"labels": [{"name": "host", "value": "box.local"}]}), encoding="utf-8"
            )
            return SimpleNamespace(returncode=pytest_rc)
        if cmd[:2] == ["allure", "generate"]:
            events.append("generate")
            # Sanitization must already have stripped host before allure generate compiles HTML.
            data = json.loads((tmp_path / ".cache/allure-results/1-result.json").read_text(encoding="utf-8"))
            assert data["labels"] == []
            return SimpleNamespace(returncode=qg_rc)
        if cmd[:2] == ["allure", "log"]:
            events.append("log")
            return SimpleNamespace(returncode=log_rc)
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(report_bdd.subprocess, "run", fake_run)
    assert report_bdd.main([]) == expected_rc
    assert events == (["pytest", "generate", "log"] if expect_allure else ["pytest"])


@pytest.mark.parametrize("starter", STARTERS)
def test_secret_scan_covers_untracked_files(tmp_path: Path, starter: str) -> None:
    env = materialize(tmp_path, starter)
    betterleaks = subprocess.check_output(["mise", "which", "betterleaks"], cwd=ROOT, text=True, timeout=60).strip()
    env["PATH"] = f"{Path(betterleaks).parent}{os.pathsep}{env['PATH']}"
    env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})
    assert run(tmp_path, env, "git", "init", "-q").returncode == 0
    (tmp_path / ".betterleaks.toml").write_text(
        '[[rules]]\nid = "fixture"\ndescription = "Synthetic fixture"\nregex = "fixture-credential-[0-9]+"\n'
    )
    assert run(tmp_path, env, "mise", "run", "check:leaks").returncode == 0
    secret = tmp_path / "untracked.txt"
    secret.write_text("fixture-credential-12345\n")
    untracked = run(tmp_path, env, "mise", "run", "check:leaks")
    assert untracked.returncode != 0
    assert "fixture-credential-12345" not in untracked.stdout + untracked.stderr


def test_python_staged_formatters_preserve_file_arguments(tmp_path: Path) -> None:
    env = materialize(tmp_path, "python")
    _route_uv_to_ruff(tmp_path, env)
    selected = tmp_path / "chosen space ' ; $(touch injected).py"
    unrelated = tmp_path / "unrelated.py"
    text = "import sys\nimport os\nx=1\n"
    selected.write_text(text)
    unrelated.write_text(text)
    hooks = yaml.safe_load((ROOT / "skills/python/references/foundation/templates/lefthook.yml").read_text())[
        "pre-commit"
    ]["jobs"]
    formatters = [hook for hook in hooks if "**/*.py" in hook.get("glob", "")]
    assert formatters
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
    env = materialize(tmp_path, "mise.toml", prefix="format:python")
    _route_uv_to_ruff(tmp_path, env)
    selected = tmp_path / "chosen space ' ; $(touch injected).py"
    unrelated = tmp_path / "unrelated.py"
    text = "import os\nx=1\n"
    selected.write_text(text)
    unrelated.write_text(text)
    hooks = yaml.safe_load((ROOT / "lefthook.yml").read_text())["pre-commit"]["jobs"]
    formatters = [hook for hook in hooks if "**/*.py" in hook.get("glob", "")]
    assert formatters
    for hook in formatters:
        assert hook["run"].endswith(" {staged_files}")
        assert hook["stage_fixed"] is True
        result = run(tmp_path, env, "mise", "run", hook["run"].split()[2], selected.name)
        assert result.returncode == 0, result.stderr
    # Ruff's defaults apply in the fixture: the safe fix drops the unused import, then formatting reflows.
    assert selected.read_text() == "x = 1\n"
    assert unrelated.read_text() == text
    assert not (tmp_path / "injected").exists()
    assert run(tmp_path, env, "mise", "run", "format:python").returncode == 0
    assert unrelated.read_text() == "x = 1\n"


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
    hooks = yaml.safe_load((ROOT / "lefthook.yml").read_text())["pre-commit"]["jobs"]
    [hook] = [hook for hook in hooks if hook.get("glob") == "**/*.lua"]
    result = run(tmp_path, env, "mise", "run", hook["run"].split()[2], str(selected))
    assert result.returncode == 0, result.stderr
    assert selected.read_text() != source
    assert unrelated.read_text() == source
    assert run(tmp_path, env, "mise", "run", "format:lua").returncode == 0
    assert unrelated.read_text() != source


def test_repository_shell_hook_preserves_unselected_files(tmp_path: Path) -> None:
    env = materialize(tmp_path, "mise.toml", prefix="format:shell")
    shfmt = subprocess.check_output(["mise", "which", "shfmt"], cwd=ROOT, text=True, timeout=60).strip()
    env["PATH"] = f"{Path(shfmt).parent}:{env['PATH']}"
    selected = tmp_path / "run_selected space ' ; $(touch injected).sh"
    unrelated = tmp_path / "run_unrelated.sh"
    source = "#!/bin/sh\nprintf   '%s\\n'   hello\n"
    selected.write_text(source)
    unrelated.write_text(source)
    hooks = yaml.safe_load((ROOT / "lefthook.yml").read_text())["pre-commit"]["jobs"]
    [hook] = [hook for hook in hooks if hook.get("run", "").startswith("mise run format:shell ")]
    assert hook["run"].endswith(" {staged_files}")
    assert hook["stage_fixed"] is True
    result = run(tmp_path, env, "mise", "run", hook["run"].split()[2], selected.name)
    assert result.returncode == 0, result.stderr
    assert selected.read_text() != source
    assert unrelated.read_text() == source
    assert not (tmp_path / "injected").exists()
    (tmp_path / "install.sh").write_text(source)
    (tmp_path / "dot_local/bin").mkdir(parents=True)
    (tmp_path / "dot_local/bin/executable_wrapper").write_text(source)
    assert run(tmp_path, env, "mise", "run", "format:shell").returncode == 0
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


@pytest.mark.parametrize("starter_path", DOCS_STARTERS)
def test_docs_serve_starters_validate_and_honor_port_override(tmp_path: Path, starter_path: str) -> None:
    shutil.copy2(ROOT / starter_path, tmp_path / "mise.toml")
    mise = shutil.which("mise")
    assert mise is not None
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    uv = bin_dir / "uv"
    uv.write_text(
        "#!/usr/bin/env python3\nimport json, sys\nfrom pathlib import Path\n"
        'Path("uv_args.json").write_text(json.dumps(sys.argv[1:]))\n'
    )
    uv.chmod(0o755)
    base_env = {
        "PATH": os.pathsep.join([str(bin_dir), str(Path(mise).parent), str(Path(sys.executable).parent), os.defpath]),
        "HOME": str(tmp_path),
        "MISE_CONFIG_DIR": str(tmp_path / "config"),
        "MISE_STATE_DIR": str(tmp_path / "mise-state"),
        "MISE_TRUSTED_CONFIG_PATHS": str(tmp_path),
    }
    assert run(tmp_path, base_env, "mise", "tasks", "validate").returncode == 0
    assert run(tmp_path, base_env, "mise", "run", "serve:docs").returncode == 0
    assert json.loads((tmp_path / "uv_args.json").read_text()) == [
        "run",
        "--locked",
        "zensical",
        "serve",
        "-a",
        "127.0.0.1:8000",
    ]
    assert run(tmp_path, base_env | {"PORT": "9123"}, "mise", "run", "serve:docs").returncode == 0
    assert json.loads((tmp_path / "uv_args.json").read_text()) == [
        "run",
        "--locked",
        "zensical",
        "serve",
        "-a",
        "127.0.0.1:9123",
    ]
