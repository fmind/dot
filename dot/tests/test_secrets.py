"""Scoped credential precedence and subprocess behavior with synthetic secrets only."""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from fmind_dot.config import Config
from fmind_dot.errors import DotError
from fmind_dot.secrets import personal_token

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def secret_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("DOT_CONFIG_PATH", raising=False)
    for name in tuple(os.environ):
        if name in {"UV_PUBLISH_TOKEN", "TEST_API_KEY", "OTHER_API_KEY"}:
            monkeypatch.delenv(name)
    directory = tmp_path / ".config/dot/secrets"
    directory.mkdir(parents=True, mode=0o700)
    for name in ("TEST_API_KEY", "OTHER_API_KEY"):
        path = directory / name
        path.write_text("synthetic-personal\n")
        path.chmod(0o600)
    return tmp_path


def invoke_process(home: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "fmind_dot", *args],
        cwd=home,
        env={**os.environ, "PYTHONPATH": str(ROOT / "dot/src")},
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def test_scoped_key_arguments_stdio_and_exit_status(secret_home: Path) -> None:
    child = (
        "import os,sys; "
        "assert os.environ['TEST_API_KEY'] == 'synthetic-personal'; "
        "assert 'OTHER_API_KEY' not in os.environ; "
        "assert sys.argv[1:] == ['a b', '$(touch nope)', '--flag']; "
        "print('child output'); print('child error', file=sys.stderr); sys.exit(7)"
    )
    result = invoke_process(
        secret_home,
        "secret",
        "run",
        "TEST_API_KEY",
        "--",
        sys.executable,
        "-c",
        child,
        "a b",
        "$(touch nope)",
        "--flag",
    )
    assert result.returncode == 7, result.stderr
    assert result.stdout == "child output\n"
    assert result.stderr == "child error\n"
    assert "TEST_API_KEY" not in os.environ
    assert not (secret_home / "nope").exists()


def test_scoped_key_ignores_invalid_configuration(secret_home: Path) -> None:
    (secret_home / ".config/dot.yaml").write_text("unknown_key: true\n")
    child = "import os,sys; sys.exit(0 if os.environ['TEST_API_KEY'] == 'synthetic-personal' else 9)"
    result = invoke_process(secret_home, "secret", "run", "TEST_API_KEY", "--", sys.executable, "-c", child)
    assert result.returncode == 0, result.stderr


def test_customer_environment_wins_without_reading_personal_file(
    secret_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (secret_home / ".config/dot/secrets/TEST_API_KEY").unlink()
    monkeypatch.setenv("TEST_API_KEY", "synthetic-customer")
    result = invoke_process(
        secret_home,
        "secret",
        "run",
        "TEST_API_KEY",
        "--",
        sys.executable,
        "-c",
        "import os; assert os.environ['TEST_API_KEY'] == 'synthetic-customer'",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == result.stderr == ""


def test_explicit_empty_does_not_fall_back(secret_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_API_KEY", "")
    result = invoke_process(secret_home, "secret", "run", "TEST_API_KEY", "--", sys.executable, "-c", "print('ran')")
    assert result.returncode == 1
    assert result.stdout == ""
    assert "empty" in result.stderr
    assert "synthetic-personal" not in result.stderr


@pytest.mark.parametrize(
    "kind", ["missing", "public", "link", "fifo", "directory", "large", "nul", "multiline", "encoding"]
)
def test_invalid_secret_fails_before_launch(secret_home: Path, kind: str) -> None:
    path = secret_home / ".config/dot/secrets/TEST_API_KEY"
    if kind in {"missing", "link", "fifo", "directory"}:
        path.unlink()
    if kind == "link":
        path.symlink_to(path.with_name("OTHER_API_KEY"))
    elif kind == "fifo":
        os.mkfifo(path)
    elif kind == "directory":
        path.mkdir()
    elif kind == "public":
        path.chmod(0o644)
    elif kind in {"large", "nul", "multiline", "encoding"}:
        path.write_bytes({"large": b"x" * 65537, "nul": b"x\0y", "multiline": b"x\ny", "encoding": b"\xff"}[kind])
    result = invoke_process(secret_home, "secret", "run", "TEST_API_KEY", "--", sys.executable, "-c", "print('ran')")
    assert result.returncode == 1
    assert result.stdout == ""
    assert "synthetic-personal" not in result.stderr


@pytest.mark.parametrize("name", ["../TEST_API_KEY", "bad-name", "UV_PUBLISH_TOKEN"])
def test_disallowed_name(secret_home: Path, name: str) -> None:
    result = invoke_process(secret_home, "secret", "run", name, "--", sys.executable, "-c", "print('ran')")
    assert result.returncode == 2
    assert result.stdout == ""


def test_missing_tool_does_not_read_secret(secret_home: Path) -> None:
    result = invoke_process(secret_home, "secret", "run", "MISSING_SECRET", "--", "nonexistent-dot-test-tool")
    assert result.returncode == 1
    assert "required tools are missing" in result.stderr


@pytest.mark.parametrize("arguments", [["secret", "publish", "--dry-run"], ["secret", "publish", "dist/x.whl"]])
def test_personal_pypi_publishing_is_retired(secret_home: Path, arguments: list[str]) -> None:
    # Packages publish through PyPI Trusted Publishing; no command supplies a personal upload token.
    result = invoke_process(secret_home, *arguments)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "synthetic-personal" not in result.stderr
    assert not (ROOT / "dot_config/dot/private_secrets/encrypted_private_UV_PUBLISH_TOKEN.age").exists()


def test_doctor_does_not_require_ambient_api_keys() -> None:
    config = Config()
    assert config.doctor.env_vars.required == []
    assert not any("TOKEN" in name or "API_KEY" in name for name in config.doctor.env_vars.optional)


def test_shell_secret_exports_are_retired() -> None:
    conf = ROOT / "dot_config/fish/conf.d"
    # chezmoi deletes the legacy exporting file instead of deploying a placeholder.
    assert (conf / "remove_secrets.fish").read_text() == ""
    assert not (conf / "private_secrets.fish").exists()
    # Any `set` that exports (-x, -gx, -g -x, --export) a token-like name is a regression.
    export = re.compile(r"\bset\s+(?:-{1,2}\w+\s+)*?(?:-\w*x\w*|--export)\s+(?:-{1,2}\w+\s+)*\w*(TOKEN|API_KEY)")
    for script in (ROOT / "dot_config/fish").rglob("*.fish*"):
        assert not export.search(script.read_text()), script


def test_environment_token_rejects_control_characters(secret_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert Path.home() == secret_home
    monkeypatch.setenv("TEST_API_KEY", "synthetic\nsecret")
    with pytest.raises(DotError, match="line break"):
        personal_token("TEST_API_KEY")


@pytest.mark.parametrize("login", [None, "kaggle.json", "credentials.json", "no-age-key"])
def test_native_seeds_preserve_subsequent_customer_logins(tmp_path: Path, login: str | None) -> None:
    source = tmp_path / "source"
    home = tmp_path / "home"
    home.mkdir()
    config = tmp_path / "chezmoi.toml"
    config.write_text("")
    shutil.copytree(ROOT / ".chezmoitemplates", source / ".chezmoitemplates")
    shutil.copyfile(ROOT / ".chezmoiignore", source / ".chezmoiignore")
    if login != "no-age-key":
        key = home / ".config/chezmoi/key.txt"
        key.parent.mkdir(parents=True)
        key.touch()  # Only the existence check is used: all fixture sources are synthetic plaintext.
    if login in {"kaggle.json", "credentials.json"}:
        existing = home / ".kaggle" / login
        existing.parent.mkdir(parents=True)
        existing.write_text("{}")
    targets = {
        "dot_cache/private_huggingface/create_encrypted_private_token.age": ".cache/huggingface/token",
        "private_dot_kaggle/create_encrypted_private_access_token.age": ".kaggle/access_token",
        "dot_local/share/private_opencode/create_encrypted_private_auth.json.age": ".local/share/opencode/auth.json",
    }
    # Keep the real deployment names/attributes but substitute synthetic plaintext for ciphertext.
    for relative in targets:
        assert (ROOT / relative).is_file()
        path = source / relative.replace("encrypted_", "").removesuffix(".age")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic-personal\n")
    command = [
        "chezmoi",
        "apply",
        "--force",
        "--source",
        str(source),
        "--destination",
        str(home),
        "--config",
        str(config),
    ]
    environment = {**os.environ, "HOME": str(home)}
    subprocess.run(command, check=True, capture_output=True, timeout=15, env=environment)
    if login == "no-age-key":
        assert all(not (home / relative).exists() for relative in targets.values())
        return
    if login in {"kaggle.json", "credentials.json"}:
        assert not (home / ".kaggle/access_token").exists()
        targets = {key: value for key, value in targets.items() if value != ".kaggle/access_token"}
    for relative in targets.values():
        path = home / relative
        assert path.read_text() == "synthetic-personal\n"
        assert path.stat().st_mode & 0o777 == 0o600
        path.write_text("synthetic-customer\n")
    subprocess.run(command, check=True, capture_output=True, timeout=15, env=environment)
    for relative in targets.values():
        assert (home / relative).read_text() == "synthetic-customer\n"
