"""Exercise interactive aliases without loading private shell configuration."""

import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

SHELL_ONLY_ENV = frozenset(
    {
        "EDITOR",
        "GLAMOUR_STYLE",
        "LANG",
        "LESS",
        "LESSHISTFILE",
        "LG_CONFIG_FILE",
        "MANPAGER",
        "PAGER",
        "PUPPETEER_EXECUTABLE_PATH",
        "SHELL",
        "VISUAL",
        "XDG_CONFIG_HOME",
    }
)


def test_fish_aliases_load_without_errors() -> None:
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            "fish",
            "--no-config",
            "--interactive",
            "--command",
            # abbr --query succeeds when any name exists, so check each one.
            (
                "source dot_config/fish/conf.d/aliases.fish; "
                "for name in a ac ai ap f h ha hc hd hh ho hp hs i j ux vd vi; "
                "abbr --query $name; or echo missing $name >&2; end"
            ),
        ],
        cwd=root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    # Fish can return success after an invalid abbr option in a sourced file.
    assert result.stderr == "", result.stderr
    assert result.returncode == 0, result.stdout


@pytest.mark.skipif(sys.platform != "darwin", reason="Homebrew paths exist only on macOS")
def test_fish_paths_keep_homebrew_ahead_of_usr_local(tmp_path: Path) -> None:
    homebrew, usr_local = "/opt/homebrew/bin", "/usr/local/bin"
    if not (Path(homebrew).is_dir() and Path(usr_local).is_dir()):
        pytest.skip("both Homebrew and /usr/local bin directories are required")
    # Resolve fish before the test replaces PATH with the system directories under test.
    fish = shutil.which("fish") or "fish"
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        # Fish rebuilds PATH from fish_user_paths in its shared config, so isolate only user configuration.
        [fish, "--command", "source dot_config/fish/conf.d/paths.fish; string join \\n -- $PATH"],
        cwd=root,
        env={**os.environ, "PATH": f"{usr_local}:/usr/bin:/bin:{homebrew}", "XDG_CONFIG_HOME": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    paths = result.stdout.splitlines()
    assert paths.index(homebrew) < paths.index(usr_local), paths


@pytest.mark.parametrize("exit_status", [0, 1])
def test_zellij_exit_returns_to_shell_without_reattaching(tmp_path: Path, exit_status: int) -> None:
    root = Path(__file__).resolve().parents[2]
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    # Avoid starting real shell integrations or touching their caches.
    for name in ("mise", "fzf", "atuin", "starship", "zoxide"):
        executable = bin_dir / name
        executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        executable.chmod(0o755)
    zellij = bin_dir / "zellij"
    zellij.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$*" >> "$ZELLIJ_TEST_CALLS"\nexit "$ZELLIJ_TEST_STATUS"\n',
        encoding="utf-8",
    )
    zellij.chmod(0o755)
    calls = tmp_path / "calls"
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"ZELLIJ", "TMUX", "NVIM", "SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY"}
    }
    env.update(
        HOME=str(tmp_path),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        ZELLIJ_TEST_BIN=str(bin_dir),
        ZELLIJ_TEST_CALLS=str(calls),
        ZELLIJ_TEST_STATUS=str(exit_status),
        TERM_PROGRAM="ghostty",
    )
    result = subprocess.run(
        [
            "fish",
            "--no-config",
            "--interactive",
            "--command",
            (
                'set -gx PATH "$ZELLIJ_TEST_BIN" $PATH; '
                "source dot_config/fish/conf.d/plugins.fish; "
                "emit fish_prompt; echo shell-survived; emit fish_prompt; echo second-prompt"
            ),
        ],
        cwd=root,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == "", result.stderr
    assert result.stdout.splitlines() == ["shell-survived", "second-prompt"]
    assert calls.read_text(encoding="utf-8").splitlines() == ["attach --create main"]


def test_fish_env_exports_stay_mirrored_in_mise_config(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    mise_env = {
        key: str(value).replace("{{env.HOME}}", str(tmp_path))
        for key, value in tomllib.loads((root / "dot_config/mise/config.toml").read_text(encoding="utf-8"))[
            "env"
        ].items()
    }
    fish = shutil.which("fish") or "fish"
    base_env = {"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"}
    baseline = subprocess.run(
        [fish, "--no-config", "--command", "env -0"],
        cwd=root,
        env=base_env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    sourced = subprocess.run(
        [fish, "--no-config", "--command", "source dot_config/fish/conf.d/env.fish; env -0"],
        cwd=root,
        env=base_env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    before = dict(entry.split("=", 1) for entry in baseline.stdout.split("\0") if "=" in entry)
    after = dict(entry.split("=", 1) for entry in sourced.stdout.split("\0") if "=" in entry)
    exported = {key: value for key, value in after.items() if before.get(key) != value and key not in SHELL_ONLY_ENV}
    assert exported
    assert {key: mise_env.get(key) for key in exported} == exported


def test_fish_env_repairs_broken_shell_and_preserves_valid_login_shell(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    fish = shutil.which("fish") or "fish"
    repaired = subprocess.run(
        [fish, "--no-config", "--command", "source dot_config/fish/conf.d/env.fish; printf '%s' $SHELL"],
        cwd=root,
        env={"HOME": str(tmp_path), "PATH": "/usr/bin:/bin", "SHELL": str(tmp_path / "missing-fish")},
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    assert Path(repaired.stdout).is_file()
    assert os.access(repaired.stdout, os.X_OK)

    preserved = subprocess.run(
        [fish, "--no-config", "--command", "source dot_config/fish/conf.d/env.fish; printf '%s' $SHELL"],
        cwd=root,
        env={"HOME": str(tmp_path), "PATH": "/usr/bin:/bin", "SHELL": "/bin/sh"},
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    assert preserved.stdout == "/bin/sh"


def test_agy_wrapper_isolates_mise_installs_and_preserves_parent_shell(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    shims = tmp_path / ".local/share/mise/shims"
    installs = tmp_path / ".local/share/mise/installs/python/3.14/bin"
    other = tmp_path / "other"
    for directory in (shims, installs, other):
        directory.mkdir(parents=True)
    agy_bin = other / "agy"
    agy_bin.write_text(
        "#!/bin/sh\n"
        'printf "PATH=%s\\n" "$PATH"\n'
        'printf "MISE_SHELL=%s\\n" "${MISE_SHELL:-unset}"\n'
        'printf "__MISE_DIFF=%s\\n" "${__MISE_DIFF:-unset}"\n'
        'printf "GH_PROMPT_DISABLED=%s\\n" "${GH_PROMPT_DISABLED:-unset}"\n'
        'printf "CLOUDSDK_CORE_DISABLE_PROMPTS=%s\\n" "${CLOUDSDK_CORE_DISABLE_PROMPTS:-unset}"\n'
        'printf "ARGS=%s\\n" "$*"\n',
        encoding="utf-8",
    )
    agy_bin.chmod(0o755)
    script = (
        f'set -gx PATH "{installs}" "{other}" "{shims}" /usr/bin /bin; '
        "set -gx MISE_SHELL fish; "
        "set -gx __MISE_DIFF eJyr; "
        "source dot_config/fish/functions/agy.fish; "
        "agy --version; "
        'printf "AFTER_PATH=%s\\n" (string join : -- $PATH); '
        'printf "AFTER_MISE_SHELL=%s\\n" "$MISE_SHELL"\n'
    )
    fish = shutil.which("fish") or "fish"
    result = subprocess.run(
        [fish, "--no-config", "--interactive", "--command", script],
        cwd=root,
        env={"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"},
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    assert result.stderr == "", result.stderr
    lines = dict(line.split("=", 1) for line in result.stdout.splitlines())
    child_path = lines["PATH"].split(":")
    assert child_path[0] == str(shims)
    assert child_path.count(str(shims)) == 1
    assert str(installs) not in child_path
    assert lines["MISE_SHELL"] == "unset"
    assert lines["__MISE_DIFF"] == "unset"
    assert lines["GH_PROMPT_DISABLED"] == "1"
    assert lines["CLOUDSDK_CORE_DISABLE_PROMPTS"] == "1"
    assert lines["ARGS"] == "--version"
    assert str(installs) in lines["AFTER_PATH"].split(":")
    assert lines["AFTER_MISE_SHELL"] == "fish"
