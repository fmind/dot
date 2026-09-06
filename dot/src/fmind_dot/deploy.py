"""Build and install the dot wheel with its exact hashed runtime dependency graph."""

from __future__ import annotations

import fcntl
import hashlib
import os
import pathlib
import shutil
import subprocess
import sys
import uuid

PYTHON_VERSION = "3.14"
SLOTS = ("venv-a", "venv-b")


def _run(command: list[str], *, cwd: pathlib.Path, environment: dict[str, str]) -> None:
    # Every caller constructs the executable and arguments from trusted local paths.
    subprocess.run(command, cwd=cwd, env=environment, check=True)  # noqa: S603 # nosemgrep: dangerous-subprocess-use-audit


def _clean_environment() -> dict[str, str]:
    # A deploy must follow this checkout's lock, independent of an active venv or user uv overrides.
    active_environment = os.environ.get("VIRTUAL_ENV")
    blocked = {"PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV"}
    environment = {key: value for key, value in os.environ.items() if key not in blocked and not key.startswith("UV_")}
    if active_environment and (path_value := environment.get("PATH")):
        active_bin = os.path.normcase(str((pathlib.Path(active_environment).expanduser() / "bin").absolute()))
        environment["PATH"] = os.pathsep.join(
            entry
            for entry in path_value.split(os.pathsep)
            if os.path.normcase(str(pathlib.Path(entry).expanduser().absolute())) != active_bin
        )
    environment["UV_NO_CONFIG"] = "1"
    return environment


def _wheel(directory: pathlib.Path) -> pathlib.Path:
    wheels = list(directory.glob("fmind_dot-*.whl"))
    if len(wheels) != 1 or wheels[0].is_symlink() or not wheels[0].is_file():
        raise RuntimeError("expected exactly one regular fmind-dot wheel from the deployment build")
    return wheels[0].resolve(strict=True)


def _package_digest(directory: pathlib.Path) -> str:
    files = sorted(path for path in directory.rglob("*.py") if path.is_file())
    if not files:
        raise FileNotFoundError(directory)
    digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(directory).as_posix().encode()
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _install_basis_digest(source: pathlib.Path) -> str:
    digest = hashlib.sha256()
    for name, content in (
        ("package", _package_digest(source / "dot/src/fmind_dot").encode()),
        ("pyproject", (source / "dot/pyproject.toml").read_bytes()),
        ("lock", (source / "dot/uv.lock").read_bytes()),
    ):
        encoded_name = name.encode()
        digest.update(len(encoded_name).to_bytes(4, "big"))
        digest.update(encoded_name)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _uv_executable(candidate: pathlib.Path | None, environment: dict[str, str]) -> pathlib.Path:
    selected = str(candidate) if candidate is not None else shutil.which("uv", path=environment.get("PATH"))
    if not selected:
        raise RuntimeError("required tool is not installed: uv")
    path = pathlib.Path(selected).expanduser()
    if not path.is_absolute():
        raise RuntimeError(f"uv executable must be an absolute path: {path}")
    resolved = path.resolve(strict=True)
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise RuntimeError(f"uv executable is not a regular executable file: {resolved}")
    return resolved


def _active_slot(current: pathlib.Path) -> str | None:
    try:
        current.lstat()
    except FileNotFoundError:
        return None
    if not current.is_symlink():
        raise RuntimeError(f"refusing to replace non-symlink runtime selector: {current}")
    target = str(current.readlink())
    if target not in SLOTS:
        raise RuntimeError(f"unexpected runtime selector target: {target}")
    return target


def _remove_inactive(path: pathlib.Path) -> None:
    try:
        path.lstat()
    except FileNotFoundError:
        return
    if path.is_symlink() or not path.is_dir():
        raise RuntimeError(f"refusing to remove non-directory runtime slot: {path}")
    shutil.rmtree(path)


def _write_requirements(
    source: pathlib.Path,
    staging: pathlib.Path,
    environment: dict[str, str],
    uv: pathlib.Path,
    wheel: pathlib.Path,
) -> tuple[pathlib.Path, str]:
    requirements = staging / "runtime-requirements.txt"
    _run(
        [
            str(uv),
            "export",
            "--project",
            "dot",
            "--locked",
            "--no-dev",
            "--no-emit-project",
            "--format",
            "requirements.txt",
            "--no-annotate",
            "--no-header",
            "--output-file",
            str(requirements),
        ],
        cwd=source,
        environment=environment,
    )
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    with requirements.open("a", encoding="utf-8") as stream:
        stream.write(f"\nfmind-dot @ {wheel.as_uri()} \\\n    --hash=sha256:{digest}\n")
    return requirements, digest


def _build_wheel(
    source: pathlib.Path,
    staging: pathlib.Path,
    environment: dict[str, str],
    uv: pathlib.Path,
    expected_basis_sha256: str,
) -> pathlib.Path:
    wheel_directory = staging / "wheel"
    # The selected uv bundles uv_build; an offline empty cache makes any backend fallback fail closed.
    _run(
        [
            str(uv),
            "build",
            "--wheel",
            "--python",
            PYTHON_VERSION,
            "--project",
            "dot",
            "--out-dir",
            str(wheel_directory),
            "--clear",
            "--offline",
            "--no-cache",
            "--no-config",
            "--no-python-downloads",
            "--no-sources",
        ],
        cwd=source,
        environment=environment,
    )
    # A wheel is trusted only when the complete source basis still matches what the build started from.
    if _install_basis_digest(source) != expected_basis_sha256:
        raise RuntimeError("source changed while building deployment wheel")
    return _wheel(wheel_directory)


def _install_locked(
    source: pathlib.Path,
    install_root: pathlib.Path,
    environment: dict[str, str],
    uv: pathlib.Path,
) -> pathlib.Path:
    source_basis_sha256 = _install_basis_digest(source)
    current = install_root / "current"
    active = _active_slot(current)
    inactive = SLOTS[1] if active == SLOTS[0] else SLOTS[0]
    destination = install_root / inactive
    _remove_inactive(destination)
    destination.mkdir(mode=0o700)

    ready = False
    try:
        _run([str(uv), "venv", str(destination), "--python", PYTHON_VERSION], cwd=source, environment=environment)
        wheel = _build_wheel(source, destination, environment, uv, source_basis_sha256)
        requirements, wheel_sha256 = _write_requirements(source, destination, environment, uv, wheel)
        python = destination / "bin" / "python"
        _run(
            [
                str(uv),
                "pip",
                "sync",
                "--python",
                str(python),
                "--require-hashes",
                "--only-binary",
                ":all:",
                "--strict",
                str(requirements),
            ],
            cwd=source,
            environment=environment,
        )
        _run(
            [
                str(python),
                "-I",
                "-c",
                (
                    "import sys; from pathlib import Path; "
                    "from fmind_dot.system import write_install_receipt; "
                    "write_install_receipt(Path(sys.argv[1]), sys.argv[2], sys.argv[3])"
                ),
                str(source),
                wheel_sha256,
                source_basis_sha256,
            ],
            cwd=source,
            environment=environment,
        )
        _run([str(destination / "bin" / "dot"), "version"], cwd=source, environment=environment)
        ready = True

        temporary_link = install_root / f".current-{uuid.uuid4().hex}"
        try:
            temporary_link.symlink_to(inactive, target_is_directory=True)
            temporary_link.replace(current)
        finally:
            temporary_link.unlink(missing_ok=True)
    finally:
        if not ready:
            _remove_inactive(destination)
    return current / "bin" / "dot"


def install(
    source_root: pathlib.Path,
    *,
    install_root: pathlib.Path | None = None,
    uv_executable: pathlib.Path | None = None,
) -> pathlib.Path:
    """Build a verified inactive runtime slot, then atomically select it."""
    source = source_root.expanduser().resolve(strict=True)
    for required in (source / "dot" / "pyproject.toml", source / "dot" / "uv.lock"):
        if required.is_symlink() or not required.is_file():
            raise RuntimeError(f"required project file is not a regular file: {required}")
    environment = _clean_environment()
    uv = _uv_executable(uv_executable, environment)

    root = install_root or pathlib.Path.home() / ".local" / "share" / "fmind-dot"
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        raise RuntimeError(f"runtime root must be a real directory: {root}")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    root.chmod(0o700)

    lock_path = root / ".deploy.lock"
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(lock_path, flags, 0o600)
    with os.fdopen(descriptor, "r+b") as lock:
        os.fchmod(lock.fileno(), 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _install_locked(source, root, environment, uv)


def main() -> int:
    source = pathlib.Path(sys.argv[1]) if len(sys.argv) >= 2 else pathlib.Path.cwd()
    uv_executable = pathlib.Path(sys.argv[2]) if len(sys.argv) == 3 else None
    if len(sys.argv) > 3:
        sys.stderr.write("usage: deploy.py [SOURCE_ROOT [UV_EXECUTABLE]]\n")
        return 2
    try:
        entrypoint = install(source, uv_executable=uv_executable)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        sys.stderr.write(f"error: {error}\n")
        return 1
    sys.stdout.write(f"dot is ready at {entrypoint}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
