from __future__ import annotations

import base64
import csv
import hashlib
import io
import os
import pathlib
import subprocess
import zipfile
from collections.abc import Callable
from unittest import mock

import pytest

import fmind_dot.system as dot_system
from fmind_dot import deploy as deploy_dot

BUILT_WHEEL = b"wheel built from the captured source basis"


def _source(root: pathlib.Path) -> pathlib.Path:
    dot = root / "dot"
    package = dot / "src" / "fmind_dot"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (dot / "pyproject.toml").write_text('[project]\nname = "fmind-dot"\nversion = "1.0.0"\n', encoding="utf-8")
    (dot / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    dist = dot / "dist"
    dist.mkdir()
    (dist / "fmind_dot-1.0.0-py3-none-any.whl").write_bytes(b"approved local wheel")
    return root


def _trusted_uv(root: pathlib.Path) -> pathlib.Path:
    path = root / "trusted/bin/uv"
    path.parent.mkdir(parents=True)
    path.write_text("fixture\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def _fake_run(fail: str = "") -> tuple[list[list[str]], Callable[..., None]]:
    calls: list[list[str]] = []

    def run(command: list[str], *, cwd: pathlib.Path, environment: dict[str, str]) -> None:
        del cwd, environment
        calls.append(command)
        if pathlib.Path(command[0]).name == "uv" and command[1] == "venv":
            bin_dir = pathlib.Path(command[2]) / "bin"
            bin_dir.mkdir(parents=True)
            python = bin_dir / "python"
            python.write_text("fixture\n", encoding="utf-8")
            python.chmod(0o755)
            dot = bin_dir / "dot"
            dot.write_text(f"#!{python}\nfixture\n", encoding="utf-8")
            dot.chmod(0o755)
        elif pathlib.Path(command[0]).name == "uv" and command[1] == "export":
            output = pathlib.Path(command[command.index("--output-file") + 1])
            output.write_text("dependency==1.0 --hash=sha256:" + "a" * 64 + "\n", encoding="utf-8")
        elif pathlib.Path(command[0]).name == "uv" and command[1] == "build":
            output = pathlib.Path(command[command.index("--out-dir") + 1])
            output.mkdir(parents=True)
            (output / "fmind_dot-1.0.0-py3-none-any.whl").write_bytes(BUILT_WHEEL)
        if fail and fail in command:
            raise subprocess.CalledProcessError(1, command)

    return calls, run


def test_clean_environment_removes_uv_python_and_active_venv_influence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    active = tmp_path / "active"
    trusted = tmp_path / "trusted"
    monkeypatch.setenv("PATH", os.pathsep.join((str(active / "bin"), str(trusted))))
    monkeypatch.setenv("VIRTUAL_ENV", str(active))
    monkeypatch.setenv("PYTHONHOME", str(tmp_path / "python-home"))
    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "python-path"))
    monkeypatch.setenv("UV_NO_VERIFY_HASHES", "1")

    environment = deploy_dot._clean_environment()

    assert environment["PATH"] == str(trusted)
    assert environment["UV_NO_CONFIG"] == "1"
    for name in ("PYTHONHOME", "PYTHONPATH", "UV_NO_VERIFY_HASHES", "VIRTUAL_ENV"):
        assert name not in environment


def test_install_uses_explicit_uv_path_and_disables_dependency_source_builds(tmp_path: pathlib.Path) -> None:
    source = _source(tmp_path / "source")
    install_root = tmp_path / "runtime"
    trusted_uv = _trusted_uv(tmp_path)
    calls, run = _fake_run()

    with mock.patch.object(deploy_dot, "_run", side_effect=run):
        deploy_dot.install(source, install_root=install_root, uv_executable=trusted_uv)

    uv_calls = [command for command in calls if len(command) > 1 and command[1] in {"build", "export", "pip", "venv"}]
    assert uv_calls
    assert all(command[0] == str(trusted_uv.resolve()) for command in uv_calls)
    build = next(command for command in uv_calls if command[1] == "build")
    assert build[build.index("--python") + 1] == deploy_dot.PYTHON_VERSION
    assert {"--no-cache", "--no-config", "--no-python-downloads", "--no-sources", "--offline"} <= set(build)
    sync = next(command for command in uv_calls if command[1:3] == ["pip", "sync"])
    assert sync[sync.index("--only-binary") + 1] == ":all:"


def test_install_uses_hashed_sync_and_flips_between_two_runtime_slots(tmp_path: pathlib.Path) -> None:
    source = _source(tmp_path / "source")
    install_root = tmp_path / "runtime"
    trusted_uv = _trusted_uv(tmp_path)
    calls, run = _fake_run()

    with mock.patch.object(deploy_dot, "_run", side_effect=run):
        first = deploy_dot.install(source, install_root=install_root, uv_executable=trusted_uv)
        second = deploy_dot.install(source, install_root=install_root, uv_executable=trusted_uv)

    assert first == second == install_root / "current/bin/dot"
    assert str((install_root / "current").readlink()) == "venv-b"
    assert (install_root / "venv-a").is_dir()
    assert (install_root / "venv-b").is_dir()
    syncs = [command for command in calls if command[1:3] == ["pip", "sync"]]
    assert len(syncs) == 2
    assert all("--require-hashes" in command and "--strict" in command for command in syncs)
    requirements = (install_root / "venv-b/runtime-requirements.txt").read_text(encoding="utf-8")
    assert "dependency==1.0 --hash=sha256:" in requirements
    assert "fmind-dot @ file:" in requirements
    wheel_digest = hashlib.sha256(BUILT_WHEEL).hexdigest()
    assert f"--hash=sha256:{wheel_digest}" in requirements
    receipt = next(command for command in calls if "write_install_receipt" in " ".join(command))
    assert receipt[1:3] == ["-I", "-c"]
    assert receipt[-2] == wheel_digest
    assert receipt[-1] == deploy_dot._install_basis_digest(source)


def test_install_rebuilds_wheel_after_project_scripts_change(tmp_path: pathlib.Path) -> None:
    source = _source(tmp_path / "source")
    stale_wheel = next((source / "dot/dist").glob("*.whl"))
    stale_digest = hashlib.sha256(stale_wheel.read_bytes()).hexdigest()
    (source / "dot/pyproject.toml").write_text(
        '[project]\nname = "fmind-dot"\nversion = "1.0.0"\n\n[project.scripts]\ndot = "fmind_dot.cli:main"\n',
        encoding="utf-8",
    )
    install_root = tmp_path / "runtime"
    trusted_uv = _trusted_uv(tmp_path)
    calls, run = _fake_run()

    with mock.patch.object(deploy_dot, "_run", side_effect=run):
        deploy_dot.install(source, install_root=install_root, uv_executable=trusted_uv)

    builds = [command for command in calls if len(command) > 1 and command[1] == "build"]
    assert len(builds) == 1
    assert "--wheel" in builds[0]
    built_directory = pathlib.Path(builds[0][builds[0].index("--out-dir") + 1])
    assert built_directory.is_relative_to(install_root / "venv-a")
    requirements = (install_root / "venv-a/runtime-requirements.txt").read_text(encoding="utf-8")
    assert f"--hash=sha256:{hashlib.sha256(BUILT_WHEEL).hexdigest()}" in requirements
    assert f"--hash=sha256:{stale_digest}" not in requirements


def test_install_rejects_source_changed_during_wheel_build_and_preserves_active_runtime(
    tmp_path: pathlib.Path,
) -> None:
    source = _source(tmp_path / "source")
    install_root = tmp_path / "runtime"
    trusted_uv = _trusted_uv(tmp_path)
    _calls, succeeds = _fake_run()
    with mock.patch.object(deploy_dot, "_run", side_effect=succeeds):
        deploy_dot.install(source, install_root=install_root, uv_executable=trusted_uv)
    current = install_root / "current"
    before = current.readlink()
    calls, base_run = _fake_run()

    def mutate_after_build(command: list[str], *, cwd: pathlib.Path, environment: dict[str, str]) -> None:
        base_run(command, cwd=cwd, environment=environment)
        if len(command) > 1 and command[1] == "build":
            (source / "dot/pyproject.toml").write_text(
                '[project]\nname = "fmind-dot"\nversion = "1.0.0"\n\n[project.scripts]\ndot = "changed:main"\n',
                encoding="utf-8",
            )

    with (
        mock.patch.object(deploy_dot, "_run", side_effect=mutate_after_build),
        pytest.raises(RuntimeError, match="source changed while building deployment wheel"),
    ):
        deploy_dot.install(source, install_root=install_root, uv_executable=trusted_uv)

    assert current.readlink() == before
    assert not (install_root / "venv-b").exists()
    assert all(command[1] != "export" for command in calls)


def test_published_console_script_keeps_its_interpreter_path(tmp_path: pathlib.Path) -> None:
    source = _source(tmp_path / "source")
    install_root = tmp_path / "runtime"
    trusted_uv = _trusted_uv(tmp_path)
    _calls, run = _fake_run()

    with mock.patch.object(deploy_dot, "_run", side_effect=run):
        entrypoint = deploy_dot.install(source, install_root=install_root, uv_executable=trusted_uv)

    interpreter = pathlib.Path(entrypoint.read_text(encoding="utf-8").splitlines()[0].removeprefix("#!"))
    assert interpreter == install_root / "venv-a/bin/python"
    assert interpreter.is_file()


def test_install_snapshots_source_basis_before_export(tmp_path: pathlib.Path) -> None:
    source = _source(tmp_path / "source")
    install_root = tmp_path / "runtime"
    trusted_uv = _trusted_uv(tmp_path)
    original_basis = dot_system._install_basis_digest(source)
    calls, base_run = _fake_run()

    def mutate_after_export(command: list[str], *, cwd: pathlib.Path, environment: dict[str, str]) -> None:
        base_run(command, cwd=cwd, environment=environment)
        if len(command) > 1 and command[1] == "export":
            (source / "dot/uv.lock").write_text("version = 2\n", encoding="utf-8")

    with mock.patch.object(deploy_dot, "_run", side_effect=mutate_after_export):
        deploy_dot.install(source, install_root=install_root, uv_executable=trusted_uv)

    receipt = next(command for command in calls if "write_install_receipt" in " ".join(command))
    assert deploy_dot._install_basis_digest(source) != original_basis
    assert receipt[-1] == original_basis


def test_failed_staged_sync_preserves_active_runtime(tmp_path: pathlib.Path) -> None:
    source = _source(tmp_path / "source")
    install_root = tmp_path / "runtime"
    trusted_uv = _trusted_uv(tmp_path)
    _calls, succeeds = _fake_run()
    with mock.patch.object(deploy_dot, "_run", side_effect=succeeds):
        deploy_dot.install(source, install_root=install_root, uv_executable=trusted_uv)
    current = install_root / "current"
    before = current.readlink()

    _calls, fails = _fake_run("--require-hashes")
    with mock.patch.object(deploy_dot, "_run", side_effect=fails), pytest.raises(subprocess.CalledProcessError):
        deploy_dot.install(source, install_root=install_root, uv_executable=trusted_uv)

    assert current.readlink() == before
    assert not (install_root / "venv-b").exists()


def test_install_rejects_unexpected_runtime_paths_before_mutation(tmp_path: pathlib.Path) -> None:
    source = _source(tmp_path / "source")
    install_root = tmp_path / "runtime"
    trusted_uv = _trusted_uv(tmp_path)
    install_root.mkdir()
    (install_root / "current").write_text("owned by user\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="non-symlink runtime selector"):
        deploy_dot.install(source, install_root=install_root, uv_executable=trusted_uv)


def _wheel(root: pathlib.Path, *, content: bytes) -> pathlib.Path:
    distribution = "hash_probe"
    version = "1.0.0"
    dist_info = f"{distribution}-{version}.dist-info"
    files = {
        f"{distribution}/__init__.py": content,
        f"{dist_info}/METADATA": b"Metadata-Version: 2.3\nName: hash-probe\nVersion: 1.0.0\n",
        f"{dist_info}/WHEEL": b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
    }
    records: list[tuple[str, str, str]] = []
    for name, body in files.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(body).digest()).rstrip(b"=").decode()
        records.append((name, f"sha256={digest}", str(len(body))))
    records.append((f"{dist_info}/RECORD", "", ""))
    record = io.StringIO()
    csv.writer(record, lineterminator="\n").writerows(records)
    files[f"{dist_info}/RECORD"] = record.getvalue().encode()
    path = root / f"{distribution}-{version}-py3-none-any.whl"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, body in files.items():
            archive.writestr(name, body)
    return path


def test_uv_hashed_sync_rejects_unapproved_same_version_artifact(tmp_path: pathlib.Path) -> None:
    wheel = _wheel(tmp_path, content=b'VALUE = "approved"\n')
    approved_hash = hashlib.sha256(wheel.read_bytes()).hexdigest()
    _wheel(tmp_path, content=b'VALUE = "tampered"\n')
    requirements = tmp_path / "requirements.txt"
    requirements.write_text(f"hash-probe==1.0.0 --hash=sha256:{approved_hash}\n", encoding="utf-8")
    environment = os.environ | {"UV_CACHE_DIR": str(tmp_path / "cache"), "UV_NO_CONFIG": "1"}
    venv = tmp_path / "venv"
    subprocess.run(["uv", "venv", "--python", deploy_dot.PYTHON_VERSION, str(venv)], env=environment, check=True)

    result = subprocess.run(
        [
            "uv",
            "pip",
            "sync",
            "--python",
            str(venv / "bin/python"),
            "--require-hashes",
            "--no-index",
            "--find-links",
            str(tmp_path),
            str(requirements),
        ],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Hash mismatch" in result.stderr


def test_uv_wheel_only_sync_rejects_a_valid_hashed_source_distribution(tmp_path: pathlib.Path) -> None:
    project = tmp_path / "project"
    package = project / "src/sdist_probe"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (project / "pyproject.toml").write_text(
        """[build-system]
requires = ["uv_build>=0.12.10,<0.13"]
build-backend = "uv_build"

[project]
name = "sdist-probe"
version = "1.0.0"
requires-python = ">=3.14"
""",
        encoding="utf-8",
    )
    environment = deploy_dot._clean_environment()
    environment["UV_CACHE_DIR"] = str(tmp_path / "cache")
    uv = deploy_dot._uv_executable(None, environment)
    dist = tmp_path / "dist"
    dist.mkdir()
    subprocess.run(
        [str(uv), "build", "--sdist", "--project", str(project), "--out-dir", str(dist)],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    sdist = next(dist.glob("sdist_probe-*.tar.gz"))
    digest = hashlib.sha256(sdist.read_bytes()).hexdigest()
    requirements = tmp_path / "requirements.txt"
    requirements.write_text(f"sdist-probe @ {sdist.as_uri()} --hash=sha256:{digest}\n", encoding="utf-8")
    venv = tmp_path / "venv"
    subprocess.run([str(uv), "venv", "--python", deploy_dot.PYTHON_VERSION, str(venv)], env=environment, check=True)

    result = subprocess.run(
        [
            str(uv),
            "pip",
            "sync",
            "--python",
            str(venv / "bin/python"),
            "--require-hashes",
            "--only-binary",
            ":all:",
            "--strict",
            str(requirements),
        ],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Building source distributions is disabled" in result.stderr
