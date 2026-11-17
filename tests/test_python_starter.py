from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _render(name: str, replacements: dict[str, str], *, owner: str = "python-stack", guide: str = "foundation") -> str:
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


def _run(root: Path, *command: str, expected_code: int = 0) -> str:
    environment: dict[str, str] = {
        **os.environ,
        "CI": "1",
        "NO_COLOR": "1",
        "UV_NO_PROGRESS": "1",
        "UV_PYTHON": sys.executable or "python",
        "UV_PYTHON_DOWNLOADS": "never",
    }
    # An inherited UV_PROJECT would redirect uv; a generated project must resolve itself.
    environment.pop("UV_PROJECT", None)
    environment.pop("VIRTUAL_ENV", None)
    environment.pop("COVERAGE_FILE", None)
    # argparse colors help when a CI forces it; help assertions read plain text.
    for forced in ("FORCE_COLOR", "PYTHON_COLORS"):
        environment.pop(forced, None)
    result = subprocess.run(
        list(command),
        cwd=str(root),
        env=environment,
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
    _write(
        project,
        "LICENSE",
        _render(license_template, replacements, owner="project-scaffolding", guide="project-license"),
    )
    _write(project, ".gitignore", _render("gitignore", replacements))
    _write(project, ".ignore", _render("ignore", replacements))
    _write(project, "AGENTS.md", _render("AGENTS.md.template", replacements))
    _write(project, "mise.toml", _render("mise.toml", replacements))
    _write(project, "lefthook.yml", _render("lefthook.yml", replacements))
    _write(project, "dprint.json", _render("dprint.json", replacements, owner="mise", guide=""))
    _write(project, ".betterleaks.toml", _render("betterleaks.toml", replacements, owner="code-security", guide=""))
    for wf in ("ci.yml", "security.yml"):
        _write(project, f".github/workflows/{wf}", _render(wf, replacements, owner="github-actions", guide="ci-cd"))
    for gh_cfg in ("dependabot.yml", "jactionlint.yaml"):
        _write(project, f".github/{gh_cfg}", _render(gh_cfg, replacements, owner="github-actions", guide=""))


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
            _render("init-api.py", replacements, owner="python-web", guide="litestar"),
        )
        _write(project, "src/starter_py/telemetry.py", _render("telemetry.py", replacements))
        _write(project, "src/starter_py/__main__.py", _render("main.py", replacements, guide="argparse"))
        _write(project, "tests/test_api.py", _render("test_api.py", replacements, owner="python-web", guide="litestar"))
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
            _render("init.py", replacements, owner="python-web", guide="litestar"),
        )
        _write(project, "src/starter_py/telemetry.py", _render("telemetry.py", replacements))
        _write(project, "src/starter_py/__main__.py", _render("main.py", replacements, guide="argparse"))
        for name in ("test_web.py", "test_integration.py"):
            _write(project, f"tests/{name}", _render(name, replacements, owner="python-web", guide="litestar"))
        _write(project, "tests/conftest.py", _render("conftest.py", replacements, owner="python-web", guide="litestar"))
        _write(project, ".env.example", _render("env.example", replacements, owner="python-web", guide="litestar"))
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
            _render("server.py", replacements, owner="agent-protocols", guide="mcp"),
        )
        _write(
            project,
            "tests/test_protocol.py",
            _render("test_protocol.py", replacements, owner="agent-protocols", guide="mcp"),
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
            _write(project, f"src/starter_py/{mod}", _render(mod, replacements, owner="python-mlops", guide=""))
        _write(
            project,
            "tests/test_pipeline.py",
            _render("test_pipeline.py", replacements, owner="python-mlops", guide=""),
        )

    _run(project, "uv", "lock")
    _run(project, "uv", "sync", "--locked")
    _run(project, "dprint", "fmt")
    _run(project, "dprint", "check")
    _run(project, "jactionlint", "--profile", "pedantic")
    _run(
        project, "betterleaks", "dir", ".", "--config", ".betterleaks.toml", "--redact=100", "--verbose", "--no-banner"
    )
    _run(project, "uv", "run", "--frozen", "validate-pyproject", "pyproject.toml")
    # The documented gate formats materialized code for the selected Python target first.
    _run(project, "uv", "run", "--frozen", "ruff", "format")
    _run(project, "uv", "run", "--frozen", "ruff", "check")
    _run(project, "uv", "run", "--frozen", "ruff", "format", "--check")
    _run(project, "uv", "run", "--frozen", "ty", "check")
    _run(project, "uv", "run", "--frozen", "deptry", ".")
    _run(
        project, "uv", "run", "--frozen", "pytest", "-m", "not integration and not e2e", "--cov", "--cov-fail-under=85"
    )
    _run(project, "uv", "build", "--clear", "--no-sources", "--out-dir", "dist")
    if profile == "library":
        # Opt-in strict docs build renders every module's API page and fails on broken cross-references.
        _write(project, "zensical.toml", _render("zensical.toml", replacements))
        _write(project, "docs/index.md", _render("docs-index.md", replacements))
        _run(project, "uv", "run", "--frozen", "zensical", "build", "--clean", "--strict")
        assert (project / "site/reference/starter_py/index.html").is_file()

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
        (ROOT / "skills/python-stack/references/python-script/templates/script.py").read_text(encoding="utf-8"),
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
            "    active_judges = 0",
            "    peak_judges = 0",
            "    async def queued_runner(_c, t):",
            "        if t == 0:",
            "            await asyncio.sleep(0.06)",
            "        return 'ok'",
            "    async def slow_judge(_c, _o):",
            "        nonlocal active_judges, peak_judges",
            "        active_judges += 1",
            "        peak_judges = max(peak_judges, active_judges)",
            "        await asyncio.sleep(0.04)",
            "        active_judges -= 1",
            "        return True",
            "    cases = [mod.EvalCase(case_id='t1', prompt='p', expected='ok', trials=3)]",
            "    res = await mod.evaluate_cases(cases, queued_runner, lambda _c, _o: True, judge=slow_judge, k=1, concurrency=1)",
            "    assert res['median_latency_ms'] < 30.0, res",
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
    clean_env = {k: v for k, v in os.environ.items() if k not in {"UV_PROJECT", "VIRTUAL_ENV", "COVERAGE_FILE"}}
    clean_env.update({"CI": "1", "NO_COLOR": "1", "UV_NO_PROGRESS": "1", "UV_PYTHON_DOWNLOADS": "never"})
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
    tpl_dir = ROOT / "skills/documentation-site/templates"
    _write(
        site,
        "pyproject.toml",
        '[project]\nname = "starter-docs"\nversion = "0.1.0"\nrequires-python = ">=3.14"\n'
        '[dependency-groups]\ndev = ["zensical>=0.1.1,<0.2"]\n',
    )
    _write(site, ".python-version", "3.14\n")
    _write(site, "zensical.toml", _render("zensical.toml", replacements, owner="documentation-site", guide=""))
    _write(site, "docs/index.md", _render("index.md", replacements, owner="documentation-site", guide=""))
    _write(site, "docs/guides/lesson.md", (tpl_dir / "lesson.md").read_text(encoding="utf-8"))
    _write(site, "includes/abbreviations.md", (tpl_dir / "abbreviations.md").read_text(encoding="utf-8"))
    _write(site, "docs/stylesheets/fmind.css", ":root { --md-primary-fg-color: #174ea6; }\n")
    _write(site, "mise.toml", (tpl_dir / "mise.toml").read_text(encoding="utf-8"))
    _write(site, "dprint.json", (ROOT / "skills/mise/templates/dprint.json").read_text(encoding="utf-8"))
    _write(site, ".betterleaks.toml", _render("betterleaks.toml", replacements, owner="code-security", guide=""))
    _write(site, ".github/workflows/docs.yml", (tpl_dir / "docs.yml").read_text(encoding="utf-8"))

    _run(site, "uv", "lock")
    _run(site, "uv", "sync", "--locked")
    _run(site, "dprint", "check")
    _run(site, "jactionlint", "--profile", "pedantic")
    _run(site, "betterleaks", "dir", ".", "--config", ".betterleaks.toml", "--redact=100", "--verbose", "--no-banner")
    _run(site, "uv", "run", "--frozen", "zensical", "build", "--clean", "--strict")
    assert (site / "site/index.html").is_file()
    assert (site / "site/llms.txt").is_file()


@pytest.mark.skipif(os.environ.get("DOT_STARTER_SMOKE") != "1", reason="run with mise run test:starters")
def test_opentofu_and_copier_starters_validate(tmp_path: Path) -> None:
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
    _write(iac, "trivy.yaml", (ROOT / "skills/code-security/references/trivy/templates/trivy.yaml").read_text())
    _write(iac, "dprint.json", (ROOT / "skills/mise/templates/dprint.json").read_text())
    _write(iac, ".betterleaks.toml", _render("betterleaks.toml", replacements, owner="code-security", guide=""))
    _write(
        iac,
        ".github/jactionlint.yaml",
        (ROOT / "skills/github-actions/templates/jactionlint.yaml").read_text(encoding="utf-8"),
    )

    _run(iac, "tofu", "fmt", "-check", "-recursive")
    _run(iac, "jactionlint", "--profile", "pedantic")
    _run(iac, "terraform-docs", ".")
    _run(iac, "dprint", "fmt", "README.md")
    _run(iac, "dprint", "check")
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

    tpl = tmp_path / "copier-tpl"
    tpl.mkdir()
    _run(tpl, "git", "init", "-q", "-b", "main")
    _write(tpl, "copier.yml", (ROOT / "skills/project-scaffolding/templates/copier.yml").read_text(encoding="utf-8"))
    _write(tpl, ".github/workflows/ci.yml", "name: Template CI\n")
    _write(tpl, "template/README.md.jinja", "# {{ slug }} ({{ package }}) by {{ holder }}\n{{ description }}\n")
    _write(tpl, "template/{{ _copier_conf.answers_file }}.jinja", "{{ _copier_answers | to_nice_yaml }}\n")
    _run(tpl, "git", "add", ".")
    _run(tpl, "git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.com", "commit", "-qm", "init")

    out = tmp_path / "copier-out"
    _run(
        tmp_path,
        "uvx",
        "--from",
        "copier>=9.19.1",
        "copier",
        "copy",
        "--defaults",
        "--data",
        "slug=demo-app",
        "--data",
        "holder=Example",
        "--data",
        "description=Demo",
        str(tpl),
        str(out),
    )
    assert "demo-app (demo_app) by Example" in (out / "README.md").read_text(encoding="utf-8")
    assert (out / ".copier-answers.yml").is_file()
    assert not (out / ".github").exists()


@pytest.mark.skipif(os.environ.get("DOT_STARTER_SMOKE") != "1", reason="run with mise run test:starters")
def test_editable_pptx_script_builds_valid_deck(tmp_path: Path) -> None:
    templates_dir = ROOT / "skills" / "draft-typst-deck" / "templates"
    script = templates_dir / "editable_deck.py"
    out = tmp_path / "editable.pptx"
    _run(tmp_path, "uv", "run", "--script", str(script), "-o", str(out))
    assert out.is_file()

    helper_path = ROOT / "skills" / "draft-typst-deck" / "scripts" / "build_typst_deck.py"
    spec = importlib.util.spec_from_file_location("build_typst_deck", helper_path)
    assert spec
    assert spec.loader
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    assert helper.inspect_pptx_metadata(out) == (3, "Architecture Decision Briefing")

    with zipfile.ZipFile(out, "r") as zf:
        notes1 = zf.read("ppt/notesSlides/notesSlide1.xml").decode()
        assert "approve Provider B" in notes1

    # Also verify rendering a standalone figure-card PNG and embedding it via --figure.
    for name in ("fmind.typ", "fmind-slides.typ", "figure-card.typ"):
        shutil.copy2(templates_dir / name, tmp_path / name)
    card_png = tmp_path / "card.png"
    assert helper.main(["render", str(tmp_path / "figure-card.typ"), "-o", str(card_png), "--allow-font-warnings"]) == 0
    out_with_fig = tmp_path / "editable-fig.pptx"
    _run(tmp_path, "uv", "run", "--script", str(script), "-o", str(out_with_fig), "--figure", str(card_png))
    assert helper.inspect_pptx_metadata(out_with_fig) == (3, "Architecture Decision Briefing")
    with zipfile.ZipFile(out_with_fig, "r") as zf:
        assert "ppt/media/image1.png" in zf.namelist()
