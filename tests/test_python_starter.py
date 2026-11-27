from __future__ import annotations

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

from repo_helpers import ROOT, load_script


def _render(name: str, replacements: dict[str, str], *, owner: str = "python", guide: str = "foundation") -> str:
    base = ROOT / "skills" / owner / ("references/" + guide if guide else "") / "templates"
    content = (base / name).read_text(encoding="utf-8")
    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)
    unresolved = {
        match.group()
        for match in re.finditer(r"<(?:owner|slug|package|description|holder|year|python_major_minor)>", content)
    }
    assert unresolved == set(), f"{name} retains placeholders: {sorted(unresolved)}"
    return content


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


_SHARED_CACHE_ENV: dict[str, str] = {}


@pytest.fixture(scope="session", autouse=True)
def _starter_caches(tmp_path_factory: pytest.TempPathFactory) -> None:
    # Share uv's flock-protected cache across xdist workers, keep dprint strictly per-worker under pytest's temp dir
    # to avoid concurrent manifest races, and stay isolated from real HOME.
    base = tmp_path_factory.getbasetemp()
    shared_root = (base.parent if os.environ.get("PYTEST_XDIST_WORKER") else base) / "dot-starter-cache"
    uv_env = os.environ.get("UV_CACHE_DIR")
    uv_cache = Path(uv_env).expanduser().resolve() if uv_env else (shared_root / "uv")
    dprint_cache = base / "dprint-cache"
    uv_cache.mkdir(parents=True, exist_ok=True)
    dprint_cache.mkdir(parents=True, exist_ok=True)
    _SHARED_CACHE_ENV.update({"UV_CACHE_DIR": str(uv_cache), "DPRINT_CACHE_DIR": str(dprint_cache)})


def _starter_env() -> dict[str, str]:
    environment: dict[str, str] = {
        **os.environ,
        **_SHARED_CACHE_ENV,
        "CI": "1",
        "NO_COLOR": "1",
        "OPENSPEC_TELEMETRY": "0",
        "UV_NO_PROGRESS": "1",
        "UV_PYTHON": sys.executable or "python",
        "UV_PYTHON_DOWNLOADS": "never",
    }
    # An inherited UV_PROJECT or UV_LOCKED would redirect or block uv; a generated project resolves itself.
    for key in ("UV_PROJECT", "UV_LOCKED", "UV_FROZEN", "VIRTUAL_ENV", "COVERAGE_FILE", "FORCE_COLOR", "PYTHON_COLORS"):
        environment.pop(key, None)
    return environment


def _run(root: Path, *command: str, expected_code: int = 0) -> str:
    result = subprocess.run(
        list(command),
        cwd=str(root),
        env=_starter_env(),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        # Resolution and installs use the network; a stalled download must fail this test.
        timeout=600,
        check=False,
    )
    assert result.returncode == expected_code, f"{' '.join(command)} failed:\n{result.stdout}{result.stderr}"
    return result.stdout


def _materialize_shared_layer(
    project: Path, replacements: dict[str, str], *, license_template: str = "PROPRIETARY"
) -> None:
    _run(project, "git", "init", "-q", "-b", "main")
    _write(project, "src/starter_py/py.typed", "")
    _write(project, "README.md", "# Starter Python\n")
    _write(project, "CHANGELOG.md", "# Changelog\n\nAll notable changes to this project are documented in this file.\n")
    _write(project, "cliff.toml", _render("cliff.toml", replacements, owner="git-delivery", guide=""))
    _write(
        project,
        "LICENSE",
        _render(license_template, replacements, owner="github", guide="project-license"),
    )
    _write(project, ".gitignore", _render("gitignore", replacements))
    _write(project, ".ignore", _render("ignore", replacements))
    _write(project, "AGENTS.md", _render("AGENTS.md.template", replacements))
    _write(project, "mise.toml", _render("mise.toml", replacements))
    _write(project, "lefthook.yml", _render("lefthook.yml", replacements))
    _write(project, "dprint.json", _render("dprint.json", replacements, owner="mise", guide=""))
    _write(project, ".betterleaks.toml", _render("betterleaks.toml", replacements, owner="code-security", guide=""))
    for wf in ("ci.yml", "security.yml"):
        _write(project, f".github/workflows/{wf}", _render(wf, replacements, owner="github", guide="ci-cd"))
    for gh_cfg in ("dependabot.yml", "jactionlint.yaml"):
        _write(project, f".github/{gh_cfg}", _render(gh_cfg, replacements, owner="github", guide=""))


@pytest.mark.skipif(os.environ.get("DOT_STARTER_SMOKE") != "1", reason="run with mise run test:starters")
@pytest.mark.parametrize("profile", ["library", "cli", "api", "web", "mcp", "ml"])
def test_python_starter_install_check_test_build_and_entrypoint(tmp_path: Path, profile: str) -> None:
    # HOME is tmp_path, so uv and Ruff caches must stay outside the generated project.
    project = tmp_path / "starter"
    project.mkdir()
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    replacements = {
        "<owner>": "example",
        "<slug>": "starter-py",
        "<package>": "starter_py",
        "<description>": "Starter command line application",
        "<holder>": "Fixture Author",
        "<year>": "2026",
        "<python_major_minor>": version,
    }
    manifest = _render("pyproject.toml.template", replacements)
    parsed = tomllib.loads(manifest)
    assert parsed["project"]["dependencies"] == []
    assert parsed["project"]["license"] == "LicenseRef-Proprietary"
    assert parsed["project"]["authors"] == [{"name": "Fixture Author"}]
    assert parsed["project"]["urls"]["Security"] == "https://github.com/example/starter-py/security/policy"
    assert "scripts" not in parsed["project"]
    if profile == "library":
        manifest = manifest.replace('license = "LicenseRef-Proprietary"', 'license = "MIT"')
    if profile in {"cli", "mcp"}:
        manifest = manifest.replace('source = ["starter_py"]', 'patch = ["subprocess"]\nsource = ["starter_py"]')
    if profile in {"cli", "api", "web", "mcp"}:
        manifest += '\n[project.scripts]\nstarter-py = "starter_py:main"\n'

    _write(project, "pyproject.toml", manifest)
    _write(project, ".python-version", f"{version}\n")
    _materialize_shared_layer(project, replacements, license_template="MIT" if profile == "library" else "PROPRIETARY")
    # Match bootstrap order: uv add builds the existing foundation before the profile replaces it.
    _write(project, "src/starter_py/__init__.py", _render("init-library.py", replacements))

    if profile == "library":
        _write(project, "SECURITY.md", _render("SECURITY.md", replacements, owner="github", guide=""))
        _write(project, "zensical.toml", _render("zensical.toml", replacements))
        _write(project, "docs/index.md", _render("docs-index.md", replacements))
        _run(project, "uv", "add", "--dev", "zensical>=0.1.1,<0.2", "mkdocstrings-python>=2.0.11")
        _write(project, "tests/test_library.py", _render("test_library.py", replacements))
    elif profile == "cli":
        _write(project, "src/starter_py/__init__.py", _render("init-cli.py", replacements, guide="argparse"))
        _write(project, "src/starter_py/__main__.py", _render("main.py", replacements, guide="argparse"))
        for name in ("test_smoke.py", "test_cli.py"):
            _write(project, f"tests/{name}", _render(name, replacements, guide="argparse"))
    elif profile == "api":
        _run(
            project,
            "uv",
            "add",
            "litestar>=2.25.0",
            "granian[reload,uvloop]>=2.8.8",
            "pydantic>=2.14.3",
            "pydantic-settings>=2.16.3",
            "structlog>=26.1.0",
            "opentelemetry-api>=1.45.2",
            "opentelemetry-sdk>=1.45.2",
            "opentelemetry-exporter-otlp-proto-http>=1.45.2",
        )
        _run(project, "uv", "add", "--dev", "anyio>=4.16.0")
        _write(
            project,
            "src/starter_py/__init__.py",
            _render("init-api.py", replacements, owner="python", guide="litestar"),
        )
        _write(project, "src/starter_py/telemetry.py", _render("telemetry.py", replacements))
        _write(project, "src/starter_py/__main__.py", _render("main.py", replacements, guide="argparse"))
        _write(project, "tests/test_api.py", _render("test_api.py", replacements, owner="python", guide="litestar"))
    elif profile == "web":
        _run(
            project,
            "uv",
            "add",
            "litestar>=2.25.0",
            "granian[reload,uvloop]>=2.8.8",
            "sqlalchemy[postgresql-asyncpg]>=2.1.8",
            "pydantic>=2.14.3",
            "pydantic-settings>=2.16.3",
            "structlog>=26.1.0",
            "opentelemetry-api>=1.45.2",
            "opentelemetry-sdk>=1.45.2",
            "opentelemetry-exporter-otlp-proto-http>=1.45.2",
        )
        _run(project, "uv", "add", "--dev", "anyio>=4.16.0", "testcontainers>=4.15.0")
        _write(
            project,
            "src/starter_py/__init__.py",
            _render("init.py", replacements, owner="python", guide="litestar"),
        )
        _write(project, "src/starter_py/telemetry.py", _render("telemetry.py", replacements))
        _write(project, "src/starter_py/__main__.py", _render("main.py", replacements, guide="argparse"))
        for name in ("test_web.py", "test_integration.py"):
            _write(project, f"tests/{name}", _render(name, replacements, owner="python", guide="litestar"))
        _write(project, "tests/conftest.py", _render("conftest.py", replacements, owner="python", guide="litestar"))
        _write(project, ".env.example", _render("env.example", replacements, owner="python", guide="litestar"))
        # Developer `.env` files must never leak into unit tests that instantiate Settings().
        _write(
            project,
            ".env",
            'DATABASE_URL=postgresql+asyncpg://env.invalid/db\nCORS_ORIGINS=["https://allowed.example"]\n',
        )
    elif profile == "mcp":
        _run(project, "uv", "add", "mcp>=2.3.0")
        _write(
            project,
            "src/starter_py/__init__.py",
            'from starter_py.server import __version__, main, server\n\n__all__ = ["__version__", "main", "server"]\n',
        )
        _write(project, "src/starter_py/__main__.py", _render("main.py", replacements, guide="argparse"))
        _write(
            project,
            "src/starter_py/server.py",
            _render("server.py", replacements, owner="agent-frameworks", guide="mcp"),
        )
        _write(
            project,
            "tests/test_protocol.py",
            _render("test_protocol.py", replacements, owner="agent-frameworks", guide="mcp"),
        )
    else:
        _run(
            project,
            "uv",
            "add",
            "polars>=2.1.0",
            "pandera[polars]>=0.36.0",
            "scikit-learn>=1.9.1",
            "pydantic-settings[yaml]>=2.16.3",
            "pydantic>=2.14.3",
        )
        for mod in ("settings.py", "pipeline.py"):
            _write(project, f"src/starter_py/{mod}", _render(mod, replacements, owner="mlops", guide=""))
        _write(
            project,
            "tests/test_pipeline.py",
            _render("test_pipeline.py", replacements, owner="mlops", guide=""),
        )

    _run(project, "uv", "lock")
    _run(project, "uv", "sync", "--locked")
    _run(project, "dprint", "fmt")
    _run(project, "dprint", "check")
    _run(project, "lefthook", "validate")
    _run(project, "lychee", "--offline", "--include-fragments", "--no-progress", "--extensions", "md", ".")
    _run(project, "typos")
    _run(project, "jactionlint", "--profile", "pedantic")
    _run(
        project, "betterleaks", "dir", ".", "--config", ".betterleaks.toml", "--redact=100", "--verbose", "--no-banner"
    )
    _run(project, "uv", "run", "--locked", "validate-pyproject", "pyproject.toml")
    # The documented gate formats materialized code for the selected Python target first.
    _run(project, "uv", "run", "--locked", "ruff", "format")
    _run(project, "uv", "run", "--locked", "ruff", "check")
    _run(project, "uv", "run", "--locked", "ruff", "format", "--check")
    _run(project, "uv", "run", "--locked", "ty", "check")
    _run(project, "uv", "run", "--locked", "deptry", ".")
    _run(
        project, "uv", "run", "--locked", "pytest", "-m", "not integration and not e2e", "--cov", "--cov-fail-under=85"
    )
    _run(project, "uv", "build", "--clear", "--no-sources", "--out-dir", "dist")
    if profile == "library":
        # Opt-in strict docs build renders every module's API page and fails on broken cross-references.
        _run(project, "uv", "run", "--locked", "zensical", "build", "--clean", "--strict")
        assert (project / "site/reference/starter_py/index.html").is_file()
        openspec_tpl = (ROOT / "skills/openspec/templates/config.yaml").read_text(encoding="utf-8")
        openspec_cfg = yaml.safe_load(openspec_tpl)
        assert openspec_cfg["schema"] == "spec-driven"
        assert {"context", "rules", "operations"} <= set(openspec_cfg)
        if shutil.which("openspec"):
            _run(project, "openspec", "init", "--tools", "none", "--no-animation")
            _write(project, "openspec/config.yaml", openspec_tpl)
            _run(project, "openspec", "validate", "--all", "--strict", "--no-interactive")
            _run(project, "openspec", "validate", "--archived", "--strict", "--no-interactive")

    runtime = project / "runtime"
    _run(project, "uv", "venv", str(runtime))
    wheel = next((project / "dist").glob("*.whl"))
    requirements = _run(project, "uv", "export", "--locked", "--no-dev", "--no-emit-project")
    req_lines = [line for line in requirements.splitlines() if line and not line.startswith("#")]
    if req_lines:
        _write(project, "runtime-requirements.txt", requirements)
        _run(
            project,
            "uv",
            "pip",
            "sync",
            "--python",
            str(runtime / "bin/python"),
            "--require-hashes",
            "runtime-requirements.txt",
        )
    _run(project, "uv", "pip", "install", "--python", str(runtime / "bin/python"), "--no-deps", str(wheel))
    outside = project / "outside"
    outside.mkdir()
    assert (
        _run(outside, str(runtime / "bin/python"), "-c", "import starter_py; print(starter_py.__version__)")
        == "0.1.0\n"
    )
    if profile in {"api", "web", "mcp"}:
        for command in ([str(runtime / "bin/starter-py")], [str(runtime / "bin/python"), "-m", "starter_py"]):
            assert _run(outside, *command, "--version") == "0.1.0\n"
            for flag in ("-h", "--help"):
                assert "starter-py" in _run(outside, *command, flag)
            _run(outside, *command, "--unknown-option", expected_code=2)
    if profile == "cli":
        for command in ([str(runtime / "bin/starter-py")], [str(runtime / "bin/python"), "-m", "starter_py"]):
            assert _run(outside, *command, "greet", "--name", "Ada") == "Hello, Ada!\n"
            assert _run(outside, *command, "--version") == "0.1.0\n"
            for flag in ("-h", "--help"):
                assert "greet" in _run(outside, *command, flag)
                assert "--name" in _run(outside, *command, "greet", flag)
            _run(outside, *command, "--unknown-option", expected_code=2)
            _run(outside, *command, expected_code=2)
        # The CLI profile ships on the standard library alone.
        assert req_lines == []


@pytest.mark.skipif(os.environ.get("DOT_STARTER_SMOKE") != "1", reason="run with mise run test:starters")
def test_pep723_script_starter_lock_audit_and_typecheck(tmp_path: Path) -> None:
    script = tmp_path / "script.py"
    script.write_text(
        (ROOT / "skills/python/references/script/templates/script.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    _run(tmp_path, "uv", "lock", "--script", str(script))
    assert (tmp_path / "script.py.lock").is_file()
    assert _run(tmp_path, "uv", "run", "--locked", "--script", str(script), "--version") == "0.1.0\n"
    _run(tmp_path, "uv", "audit", "--preview-features", "audit-command", "--locked", "--script", str(script))
    script_python = _run(tmp_path, "uv", "python", "find", "--script", str(script)).strip()
    ty_bin = str(ROOT / "dot/.venv/bin/ty")
    _run(tmp_path, ty_bin, "check", "--python", script_python, str(script))

    eval_script = tmp_path / "eval_runner.py"
    eval_script.write_text(
        (ROOT / "skills/agent-frameworks/references/evaluation/templates/eval_runner.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    _run(tmp_path, "uv", "lock", "--script", str(eval_script))
    assert (tmp_path / "eval_runner.py.lock").is_file()
    assert _run(tmp_path, "uv", "run", "--locked", "--script", str(eval_script), "--version") == "0.1.0\n"
    dataset = tmp_path / "cases.json"
    dataset.write_text(
        json.dumps([{"case_id": "c1", "prompt": "p1", "expected": "ok", "trials": 3}]),
        encoding="utf-8",
    )
    eval_out = json.loads(
        _run(tmp_path, "uv", "run", "--locked", "--script", str(eval_script), str(dataset), "--k", "2")
    )
    assert eval_out["mean_pass_at_k"] == 1.0
    assert eval_out["mean_pass_power_k"] == 1.0
    eval_python = _run(tmp_path, "uv", "python", "find", "--script", str(eval_script)).strip()
    _run(tmp_path, ty_bin, "check", "--python", eval_python, str(eval_script))

    eval_check = "\n".join(
        [
            "import asyncio, importlib.util, sys",
            "from pathlib import Path",
            "spec = importlib.util.spec_from_file_location('eval_runner', Path('eval_runner.py'))",
            "mod = importlib.util.module_from_spec(spec)",
            "assert spec.loader is not None",
            "sys.modules['eval_runner'] = mod",
            "spec.loader.exec_module(mod)",
            "assert mod.pass_power_k(3, 1, 2) == 0.0",
            "assert mod.pass_power_k(4, 3, 2) == 0.5",
            "assert mod.pass_at_k(4, 1, 2) == 0.5",
            "for bad in ((3, -1, 1), (3, 4, 1), (2, 1, 3)):",
            "    try:",
            "        mod.pass_power_k(*bad)",
            "    except ValueError:",
            "        pass",
            "    else:",
            "        raise AssertionError(f'expected ValueError for {bad}')",
            "async def run_checks():",
            "    dup = [mod.EvalCase(case_id='a', prompt='p', expected='ok', trials=2), mod.EvalCase(case_id='a', prompt='p', expected='ok', trials=2)]",
            "    try:",
            "        await mod.evaluate_cases(dup, lambda c, t: asyncio.sleep(0, result='ok'), lambda c, o: True, k=1)",
            "    except ValueError:",
            "        pass",
            "    else:",
            "        raise AssertionError('expected duplicate case_id ValueError')",
            "    short = [mod.EvalCase(case_id='s', prompt='p', expected='ok', trials=1)]",
            "    try:",
            "        await mod.evaluate_cases(short, lambda c, t: asyncio.sleep(0, result='ok'), lambda c, o: True, k=2)",
            "    except ValueError:",
            "        pass",
            "    else:",
            "        raise AssertionError('expected trials < k ValueError')",
            "    clock = [0.0]",
            "    loop = asyncio.get_running_loop()",
            "    orig_time = loop.time",
            "    loop.time = lambda: clock[0]",
            "    active_runners = 0",
            "    peak_runners = 0",
            "    async def queued_runner(_c, t):",
            "        nonlocal active_runners, peak_runners",
            "        active_runners += 1",
            "        peak_runners = max(peak_runners, active_runners)",
            "        await asyncio.sleep(0)",
            "        clock[0] += 0.050 if t == 0 else 0.010",
            "        active_runners -= 1",
            "        return 'ok'",
            "    cases = [mod.EvalCase(case_id='t1', prompt='p', expected='ok', trials=3)]",
            "    try:",
            "        qres = await mod.evaluate_cases(cases, queued_runner, lambda _c, _o: True, judge=None, k=1, concurrency=1)",
            "    finally:",
            "        loop.time = orig_time",
            "    assert peak_runners == 1, peak_runners",
            "    assert abs(qres['median_latency_ms'] - 10.0) < 1e-9, qres",
            "    active_judges = 0",
            "    peak_judges = 0",
            "    clock[0] = 0.0",
            "    loop.time = lambda: clock[0]",
            "    async def fast_runner(_c, _t):",
            "        clock[0] += 0.010",
            "        return 'ok'",
            "    async def slow_judge(_c, _o):",
            "        nonlocal active_judges, peak_judges",
            "        active_judges += 1",
            "        peak_judges = max(peak_judges, active_judges)",
            "        await asyncio.sleep(0)",
            "        clock[0] += 0.200",
            "        active_judges -= 1",
            "        return True",
            "    try:",
            "        res = await mod.evaluate_cases(cases, fast_runner, lambda _c, _o: True, judge=slow_judge, k=1, concurrency=1)",
            "    finally:",
            "        loop.time = orig_time",
            "    assert abs(res['median_latency_ms'] - 10.0) < 1e-9, res",
            "    assert peak_judges == 1, peak_judges",
            "    async def mixed_runner(_c, t):",
            "        if t == 0:",
            "            raise RuntimeError('transient failure')",
            "        if t == 1:",
            "            return mod.TrialResult(output='ok', forbidden_attempts=1, cost_usd=0.02)",
            "        return mod.TrialResult(output='ok', state={'saved': True}, trajectory=['read'], cost_usd=0.01)",
            "    mixed = await mod.evaluate_cases(cases, mixed_runner, lambda _c, r: r.output == 'ok', k=1, concurrency=2)",
            "    assert mixed['total_errors'] == 1, mixed",
            "    assert mixed['total_forbidden_attempts'] == 1, mixed",
            "    assert mixed['results'][0]['passed'] == 1, mixed",
            "    mixed_default_k = await mod.evaluate_cases(cases, mixed_runner, lambda _c, r: r.output == 'ok', concurrency=2)",
            "    assert mixed_default_k['k'] == 3 and mixed_default_k['mean_pass_at_k'] == 1.0 and mixed_default_k['mean_pass_power_k'] == 0.0, mixed_default_k",
            "asyncio.run(run_checks())",
        ]
    )
    _run(tmp_path, eval_python, "-c", eval_check)

    empty_dataset = tmp_path / "empty_cases.json"
    empty_dataset.write_text("[]", encoding="utf-8")
    short_dataset = tmp_path / "short_cases.json"
    short_dataset.write_text('[{"case_id": "c1", "prompt": "p1", "expected": "ok"}]', encoding="utf-8")
    bad_dataset = tmp_path / "bad_cases.json"
    bad_dataset.write_text('["not-a-dict"]', encoding="utf-8")
    clean_env = _starter_env()
    for cli_args in (["--trials", "1", "--k", "2", str(short_dataset)], [str(bad_dataset)], [str(empty_dataset)]):
        proc = subprocess.run(
            ["uv", "run", "--locked", "--script", str(eval_script), *cli_args],
            cwd=str(tmp_path),
            env=clean_env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert proc.returncode == 1
        assert "Error: " in proc.stderr
        assert "Traceback" not in proc.stderr


@pytest.mark.skipif(os.environ.get("DOT_STARTER_SMOKE") != "1", reason="run with mise run test:starters")
def test_standalone_zensical_docs_starter_builds_strictly(tmp_path: Path) -> None:
    site = tmp_path / "docs-starter"
    site.mkdir()
    _run(site, "git", "init", "-q", "-b", "main")
    replacements = {
        "<owner>": "example",
        "<slug>": "starter-docs",
        "<package>": "starter-docs",
        "<description>": "Starter documentation site",
        "<holder>": "Fixture Author",
        "<year>": "2026",
        "<audience>": "engineers",
        "<achieve an outcome>": "ship verified documentation",
        "<expected output>": "0.1.0",
    }
    tpl_dir = ROOT / "skills/docs/references/site/templates"
    _write(
        site,
        "pyproject.toml",
        '[project]\nname = "starter-docs"\nversion = "0.1.0"\nrequires-python = ">=3.14"\n'
        '[dependency-groups]\ndev = ["zensical>=0.1.1,<0.2"]\n',
    )
    _write(site, ".python-version", "3.14\n")
    _write(site, "zensical.toml", _render("zensical.toml", replacements, owner="docs", guide="site"))
    _write(site, "docs/index.md", _render("index.md", replacements, owner="docs", guide="site"))
    _write(site, "docs/guides/lesson.md", (tpl_dir / "lesson.md").read_text(encoding="utf-8"))
    _write(site, "includes/abbreviations.md", (tpl_dir / "abbreviations.md").read_text(encoding="utf-8"))
    _write(site, "docs/stylesheets/fmind.css", ":root { --md-primary-fg-color: #174ea6; }\n")
    _write(site, "CHANGELOG.md", "# Changelog\n\nAll notable changes to this project are documented in this file.\n")
    _write(site, "cliff.toml", _render("cliff.toml", replacements, owner="git-delivery", guide=""))
    _write(site, "mise.toml", (tpl_dir / "mise.toml").read_text(encoding="utf-8"))
    _write(site, "lefthook.yml", (tpl_dir / "lefthook.yml").read_text(encoding="utf-8"))
    _write(site, "dprint.json", (ROOT / "skills/mise/templates/dprint.json").read_text(encoding="utf-8"))
    _write(site, ".betterleaks.toml", _render("betterleaks.toml", replacements, owner="code-security", guide=""))
    _write(site, ".github/workflows/docs.yml", (tpl_dir / "docs.yml").read_text(encoding="utf-8"))

    _run(site, "uv", "lock")
    _run(site, "uv", "sync", "--locked")
    _run(site, "dprint", "check")
    _run(site, "lefthook", "validate")
    _run(site, "lychee", "--offline", "--include-fragments", "--no-progress", "--extensions", "md", ".")
    _run(site, "typos")
    _run(site, "jactionlint", "--profile", "pedantic")
    _run(site, "betterleaks", "dir", ".", "--config", ".betterleaks.toml", "--redact=100", "--verbose", "--no-banner")
    _run(site, "uv", "run", "--locked", "zensical", "build", "--clean", "--strict")
    assert (site / "site/index.html").is_file()
    assert (site / "site/llms.txt").is_file()


@pytest.mark.skipif(os.environ.get("DOT_STARTER_SMOKE") != "1", reason="run with mise run test:starters")
def test_opentofu_starter_validates(tmp_path: Path) -> None:
    iac = tmp_path / "iac"
    iac.mkdir()
    _run(iac, "git", "init", "-q", "-b", "main")
    replacements = {
        "<slug>": "demo-svc",
        "<project>": "demo-proj-123",
        "<region>": "europe-west1",
        "<holder>": "Fixture Author",
        "<year>": "2026",
    }
    iac_tpl = ROOT / "skills/infra-as-code/templates"
    file_map = {
        "README.md": "README.md",
        "tofu.yml": ".github/workflows/tofu.yml",
        "versions.tf": "versions.tf",
        "main.tf": "main.tf",
        "variables.tf": "variables.tf",
        "outputs.tf": "outputs.tf",
        "terraform.example.tfvars": "terraform.example.tfvars",
        "main.tftest.hcl": "tests/main.tftest.hcl",
        "tflint.hcl": ".tflint.hcl",
        "terraform-docs.yml": ".terraform-docs.yml",
        "gitignore": ".gitignore",
        "lefthook.yml": "lefthook.yml",
        "mise.toml": "mise.toml",
    }
    for src_name, dst_rel in file_map.items():
        text = (iac_tpl / src_name).read_text(encoding="utf-8")
        for placeholder, value in replacements.items():
            text = text.replace(placeholder, value)
        _write(iac, dst_rel, text)
    _write(iac, "LICENSE", _render("PROPRIETARY", replacements, owner="github", guide="project-license"))
    _write(iac, "CHANGELOG.md", "# Changelog\n\nAll notable changes to this project are documented in this file.\n")
    _write(iac, "cliff.toml", _render("cliff.toml", replacements, owner="git-delivery", guide=""))
    _write(iac, "trivy.yaml", (ROOT / "skills/code-security/references/trivy/templates/trivy.yaml").read_text())
    _write(iac, "dprint.json", (ROOT / "skills/mise/templates/dprint.json").read_text())
    _write(iac, ".betterleaks.toml", _render("betterleaks.toml", replacements, owner="code-security", guide=""))
    _write(
        iac,
        ".github/jactionlint.yaml",
        (ROOT / "skills/github/templates/jactionlint.yaml").read_text(encoding="utf-8"),
    )

    _run(iac, "tofu", "fmt", "-check", "-recursive")
    _run(iac, "jactionlint", "--profile", "pedantic")
    _run(iac, "terraform-docs", ".")
    _run(iac, "dprint", "fmt", "README.md")
    _run(iac, "dprint", "check")
    _run(iac, "lefthook", "validate")
    _run(iac, "lychee", "--offline", "--include-fragments", "--no-progress", "--extensions", "md", ".")
    _run(iac, "typos")
    _run(iac, "betterleaks", "dir", ".", "--config", ".betterleaks.toml", "--redact=100", "--verbose", "--no-banner")
    _run(
        iac,
        "trivy",
        "--config",
        "trivy.yaml",
        "fs",
        "--scanners",
        "misconfig",
        "--tf-vars",
        "terraform.example.tfvars",
        ".",
    )
    _run(iac, "tofu", "init", "-backend=false", "-input=false")
    _run(iac, "tofu", "validate")
    _run(iac, "tflint", "--init")
    _run(iac, "tflint", "--recursive")
    _run(iac, "tofu", "test")


@pytest.mark.skipif(os.environ.get("DOT_STARTER_SMOKE") != "1", reason="run with mise run test:starters")
def test_python_bdd_starter_validates(tmp_path: Path) -> None:
    project = tmp_path / "bdd-starter"
    project.mkdir()
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    replacements = {
        "<owner>": "example",
        "<slug>": "starter-py",
        "<package>": "starter_py",
        "<description>": "Starter BDD application",
        "<holder>": "Fixture Author",
        "<year>": "2026",
        "<python_major_minor>": version,
    }
    manifest = _render("pyproject.toml.template", replacements)
    markers_block = (
        "markers = [\n"
        '  "e2e: requires browser and live local server",\n'
        '  "integration: requires local Docker and disposable external services",\n'
        "]"
    )
    assert markers_block in manifest
    manifest = manifest.replace(
        markers_block,
        'bdd_features_base_dir = "features"\n'
        "markers = [\n"
        '  "e2e: requires browser and live local server",\n'
        '  "integration: requires local Docker and disposable external services",\n'
        '  "wip: unimplemented acceptance specs",\n'
        '  "sla: service-level acceptance budgets",\n'
        "]",
    )
    _write(project, "pyproject.toml", manifest)
    _write(project, ".python-version", f"{version}\n")
    _materialize_shared_layer(project, replacements)
    _write(
        project,
        "src/starter_py/__init__.py",
        _render("init-library.py", replacements) + '\n\ndef greet(name: str) -> str:\n    return f"Hello, {name}!"\n',
    )

    bdd_tpl = ROOT / "skills/python/references/testing/templates"
    _write(project, "allurerc.yaml", (bdd_tpl / "allurerc.yaml").read_text(encoding="utf-8"))
    _write(project, "tests/bdd/conftest.py", (bdd_tpl / "bdd-conftest.py").read_text(encoding="utf-8"))
    _write(project, "tests/bdd/report_bdd.py", (bdd_tpl / "report_bdd.py").read_text(encoding="utf-8"))
    _write(
        project,
        "features/orders.feature",
        "Feature: Order greeting\n"
        "\n"
        "  Rule: Implemented greetings meet SLA\n"
        "    @issue_42 @severity_critical @sla\n"
        "    Scenario: Greet customer cleanly\n"
        "      Given a customer named Ada\n"
        "      When the greeter runs\n"
        "      Then the greeting includes Ada\n"
        "\n"
        "  @wip\n"
        "  Rule: Future batch greetings\n"
        "    Scenario: Unimplemented batch step skips cleanly\n"
        "      Given an unimplemented batch queue\n",
    )
    _write(
        project,
        "tests/bdd/test_features.py",
        "import json\n"
        "from pathlib import Path\n"
        "\n"
        "import allure\n"
        "from pytest_bdd import given, parsers, scenarios, then, when\n"
        "\n"
        "from starter_py import greet\n"
        "\n"
        'scenarios(".")\n'
        "\n"
        "\n"
        '@given(parsers.parse("a customer named {name}"), target_fixture="customer")\n'
        "def customer_name(name: str) -> str:\n"
        "    return name\n"
        "\n"
        "\n"
        '@when("the greeter runs", target_fixture="greeting")\n'
        "def run_greeter(customer: str) -> str:\n"
        '    print(f"cwd={Path.cwd()} home={Path.home()}")\n'
        "    allure.attach(\n"
        '        json.dumps({"p95_ms": 12}, indent=2),\n'
        '        name="sla.json",\n'
        "        attachment_type=allure.attachment_type.JSON,\n"
        "    )\n"
        "    return greet(customer)\n"
        "\n"
        "\n"
        '@then(parsers.parse("the greeting includes {name}"))\n'
        "def check_greeting(greeting: str, name: str) -> None:\n"
        "    assert name in greeting\n",
    )

    _run(project, "uv", "add", "--dev", "pytest-bdd>=9.0", "allure-pytest-bdd>=2.16.2")
    _run(project, "uv", "sync", "--locked")
    _run(project, "uv", "run", "--locked", "ruff", "check")
    _run(project, "uv", "run", "--locked", "ruff", "format", "--check")
    _run(project, "uv", "run", "--locked", "ty", "check")
    pr_out = _run(
        project, "uv", "run", "--locked", "pytest", "-m", "not integration and not e2e and not wip", "tests/bdd"
    )
    assert "1 passed" in pr_out
    assert "1 deselected" in pr_out
    assert "skipped" not in pr_out
    _run(
        project,
        "uv",
        "run",
        "--locked",
        "pytest",
        "-q",
        "tests/bdd",
        "--alluredir=.cache/allure-results",
        "--allure-link-pattern=issue:https://github.com/example/starter-py/issues/{}",
    )

    results_dir = project / ".cache/allure-results"
    report_bdd = load_script("starter_report_bdd", project / "tests/bdd/report_bdd.py")
    report_bdd.sanitize_results(results_dir, cwd=project, home=Path.home())

    result_files = sorted(results_dir.glob("*-result.json"))
    assert len(result_files) == 2
    parsed = {data["name"]: data for data in (json.loads(p.read_text(encoding="utf-8")) for p in result_files)}

    passed = parsed["Greet customer cleanly"]
    assert passed["status"] == "passed"
    labels = {(lbl["name"], lbl["value"]) for lbl in passed["labels"]}
    assert ("story", "Implemented greetings meet SLA") in labels
    assert ("severity", "critical") in labels
    assert ("tag", "sla") in labels
    assert not any(lbl["name"] == "host" for lbl in passed["labels"])
    assert any(
        link.get("type") == "issue" and link.get("url") == "https://github.com/example/starter-py/issues/42"
        for link in passed.get("links", [])
    )
    json_attachments = sorted(results_dir.glob("*-attachment.json"))
    assert len(json_attachments) == 1
    assert json.loads(json_attachments[0].read_text(encoding="utf-8")) == {"p95_ms": 12}
    txt_attachments = sorted(results_dir.glob("*-attachment.txt"))
    assert txt_attachments
    assert any("cwd=. home=~" in p.read_text(encoding="utf-8") for p in txt_attachments)
    for txt_attachment in txt_attachments:
        body = txt_attachment.read_text(encoding="utf-8")
        assert str(project) not in body
        assert str(Path.home()) not in body

    wip = parsed["Unimplemented batch step skips cleanly"]
    assert wip["status"] == "skipped"
