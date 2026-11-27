"""Exercise interactive aliases without loading private shell configuration."""

import os
import pty
import re
import select
import subprocess
import sys
import time
import tomllib
from pathlib import Path

import pytest

from repo_helpers import ROOT, native_binary

_GUARDED_ENV_VARS = frozenset(
    {
        "ANTIGRAVITY_AGENT",
        "CI",
        "CLAUDECODE",
        "NVIM",
        "SSH_CLIENT",
        "SSH_CONNECTION",
        "SSH_TTY",
        "TERM",
        "TERM_PROGRAM",
        "TMUX",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
        "ZELLIJ",
    }
)

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
        "SSH_AUTH_SOCK",
        "VISUAL",
        "XDG_CONFIG_HOME",
    }
)


def _fish() -> str:
    return str(native_binary("fish") or "fish")


def _run_fish(
    command: str,
    *,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
    interactive: bool = False,
    no_config: bool = True,
    timeout: int = 15,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    argv = [_fish()]
    if no_config:
        argv.append("--no-config")
    if interactive:
        argv.append("--interactive")
    argv.extend(["--command", command])
    return subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
        check=check,
    )


def test_fish_aliases_load_without_errors() -> None:
    result = _run_fish(
        # abbr --query succeeds when any name exists, so check each one.
        (
            "source dot_config/fish/conf.d/aliases.fish; or exit 1; "
            "for name in a b c d e f g h i j k l m n o p q r s t u v w x y "
            "ac ai ap av avs avu gl hd hh hp hs la ll lt mr uf ur ux vd vi; "
            "abbr --query $name; or echo missing $name >&2; end; "
            "for name in ss z; "
            "abbr --query $name; and echo unexpected $name >&2; end; "
            "true"
        ),
        interactive=True,
        timeout=10,
    )
    # Fish can return success after an invalid abbr option in a sourced file.
    assert result.stderr == "", result.stderr
    assert result.returncode == 0, result.stdout


@pytest.mark.skipif(sys.platform != "darwin", reason="Homebrew paths exist only on macOS")
def test_fish_paths_keep_homebrew_ahead_of_usr_local(tmp_path: Path) -> None:
    homebrew, usr_local = "/opt/homebrew/bin", "/usr/local/bin"
    if not (Path(homebrew).is_dir() and Path(usr_local).is_dir()):
        pytest.skip("both Homebrew and /usr/local bin directories are required")
    # Fish rebuilds PATH from fish_user_paths in its shared config, so isolate only user configuration.
    result = _run_fish(
        "source dot_config/fish/conf.d/paths.fish; string join \\n -- $PATH",
        env={**os.environ, "PATH": f"{usr_local}:/usr/bin:/bin:{homebrew}", "XDG_CONFIG_HOME": str(tmp_path)},
        no_config=False,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    paths = result.stdout.splitlines()
    assert paths.index(homebrew) < paths.index(usr_local), paths


def _clean_fish_env(tmp_path: Path, **overrides: str) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key not in _GUARDED_ENV_VARS}
    env.update(HOME=str(tmp_path), TERM="xterm-256color")
    env.update(overrides)
    return env


def _run_fish_pty(
    command: str,
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: float = 30.0,
) -> tuple[int, str, str]:
    master, slave = pty.openpty()
    proc: subprocess.Popen[bytes] | None = None
    chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []
    try:
        proc = subprocess.Popen(
            [_fish(), "--no-config", "--interactive", "--command", command],
            cwd=cwd,
            env=env,
            stdin=slave,
            stdout=slave,
            stderr=subprocess.PIPE,
            close_fds=True,
        )
    finally:
        os.close(slave)
    try:
        assert proc.stderr is not None
        stderr_fd = proc.stderr.fileno()
        deadline = time.monotonic() + timeout
        open_fds = [master, stderr_fd]
        while open_fds:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                proc.kill()
                raise TimeoutError(f"Fish PTY timed out after {timeout}s")
            readable, _, _ = select.select(open_fds, [], [], min(0.2, remaining))
            if not readable:
                continue
            for fd in readable:
                try:
                    data = os.read(fd, 4096)
                except OSError:
                    data = b""
                if not data:
                    open_fds.remove(fd)
                elif fd == master:
                    chunks.append(data)
                else:
                    stderr_chunks.append(data)
        returncode = proc.wait(timeout=5)
        stdout = b"".join(chunks).decode("utf-8").replace("\r\n", "\n")
        stderr = b"".join(stderr_chunks).decode("utf-8")
        return returncode, stdout, stderr
    finally:
        os.close(master)
        if proc is not None:
            if proc.stderr is not None:
                proc.stderr.close()
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)


def _install_auto_zellij_stubs(tmp_path: Path) -> tuple[Path, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    # Avoid starting real shell integrations or touching their caches.
    for name in ("mise", "fzf", "atuin", "starship", "zoxide"):
        executable = bin_dir / name
        executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        executable.chmod(0o755)
    calls = tmp_path / "calls"
    zellij = bin_dir / "zellij"
    zellij.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$*" >> "$ZELLIJ_TEST_CALLS"\nexit "$ZELLIJ_TEST_STATUS"\n',
        encoding="utf-8",
    )
    zellij.chmod(0o755)
    return bin_dir, calls


@pytest.mark.parametrize("exit_status", [0, 1])
def test_zellij_exit_returns_to_shell_without_reattaching(tmp_path: Path, exit_status: int) -> None:
    bin_dir, calls = _install_auto_zellij_stubs(tmp_path)
    env = _clean_fish_env(
        tmp_path,
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        ZELLIJ_TEST_CALLS=str(calls),
        ZELLIJ_TEST_STATUS=str(exit_status),
        TERM_PROGRAM="ghostty",
    )
    returncode, stdout, stderr = _run_fish_pty(
        (
            f'set -gx PATH "{bin_dir}" $PATH; '
            "source dot_config/fish/conf.d/plugins.fish; "
            "emit fish_prompt; echo shell-survived; emit fish_prompt; echo second-prompt"
        ),
        cwd=ROOT,
        env=env,
    )
    assert returncode == 0, stderr
    assert stderr == "", stderr
    assert stdout.splitlines() == ["shell-survived", "second-prompt"]
    assert calls.read_text(encoding="utf-8").splitlines() == ["attach --create main"]


@pytest.mark.parametrize(
    "blocked_env",
    [
        {"ANTIGRAVITY_AGENT": "1"},
        {"CI": "true"},
        {"CLAUDECODE": "1"},
        {"TERM_PROGRAM": "agy"},
        {"TERM_PROGRAM": "vscode"},
        {"TERM": "dumb"},
        {"ZELLIJ": "0"},
        {"TMUX": "tmux-session"},
        {"NVIM": "nvim-server"},
        {"SSH_CONNECTION": "1.2.3.4 1 5.6.7.8 22"},
        {"SSH_CLIENT": "1.2.3.4 1 22"},
        {"SSH_TTY": "/dev/pts/0"},
    ],
)
def test_auto_zellij_skips_agent_ci_ssh_and_nested_pty_shells(tmp_path: Path, blocked_env: dict[str, str]) -> None:
    bin_dir, calls = _install_auto_zellij_stubs(tmp_path)
    env = _clean_fish_env(
        tmp_path,
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        ZELLIJ_TEST_CALLS=str(calls),
        ZELLIJ_TEST_STATUS="0",
        TERM_PROGRAM="ghostty",
    )
    env.update(blocked_env)
    returncode, stdout, stderr = _run_fish_pty(
        f'set -gx PATH "{bin_dir}" $PATH; source dot_config/fish/conf.d/plugins.fish; emit fish_prompt; echo survived',
        cwd=ROOT,
        env=env,
    )
    assert returncode == 0, stderr
    assert stderr == "", stderr
    assert stdout.splitlines() == ["survived"]
    assert not calls.exists()


def test_auto_zellij_skips_non_tty_and_attaches_when_term_program_unset_on_pty(tmp_path: Path) -> None:
    bin_dir, calls = _install_auto_zellij_stubs(tmp_path)
    env = _clean_fish_env(
        tmp_path,
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        ZELLIJ_TEST_CALLS=str(calls),
        ZELLIJ_TEST_STATUS="0",
    )
    non_tty = _run_fish(
        f'set -gx PATH "{bin_dir}" $PATH; source dot_config/fish/conf.d/plugins.fish; emit fish_prompt; echo ok',
        env=env,
        interactive=True,
    )
    assert non_tty.returncode == 0, non_tty.stderr
    assert non_tty.stderr == "", non_tty.stderr
    assert non_tty.stdout.splitlines() == ["ok"]
    assert not calls.exists()

    # Unset TERM_PROGRAM on a real TTY must still attach once.
    assert "TERM_PROGRAM" not in env
    returncode, stdout, stderr = _run_fish_pty(
        f'set -gx PATH "{bin_dir}" $PATH; source dot_config/fish/conf.d/plugins.fish; emit fish_prompt; echo attached',
        cwd=ROOT,
        env=env,
    )
    assert returncode == 0, stderr
    assert stderr == "", stderr
    assert stdout.splitlines() == ["attached"]
    assert calls.read_text(encoding="utf-8").splitlines() == ["attach --create main"]


def test_plugins_runs_live_interactive_init(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "calls"
    for name in ("mise", "fzf", "atuin", "starship", "zoxide"):
        executable = bin_dir / name
        executable.write_text(
            f'#!/bin/sh\nprintf "%s %s\\n" "{name}" "$*" >> "$PLUGIN_TEST_CALLS"\nprintf "set -g stub_{name} live\\n"\n',
            encoding="utf-8",
        )
        executable.chmod(0o755)
    env = _clean_fish_env(tmp_path, PLUGIN_TEST_CALLS=str(calls), ZELLIJ="0")
    cmd = (
        f'set -gx PATH "{bin_dir}" $PATH; '
        "source dot_config/fish/conf.d/plugins.fish; "
        'printf "mise=%s atuin=%s fzf=%s starship=%s zoxide=%s\\n" '
        '"$stub_mise" "$stub_atuin" "$stub_fzf" "$stub_starship" "$stub_zoxide"'
    )
    result = _run_fish(cmd, env=env, interactive=True)
    assert result.returncode == 0, result.stderr
    assert result.stderr == "", result.stderr
    assert result.stdout.strip() == "mise=live atuin=live fzf=live starship=live zoxide=live"
    assert calls.read_text(encoding="utf-8").splitlines() == [
        "mise activate fish",
        "fzf --fish",
        "atuin init fish --disable-ai",
        "starship init fish --print-full-init",
        "zoxide init fish",
    ]

    # A second interactive shell reuses the cached init scripts without respawning the 5 tools.
    calls.unlink()
    cached = _run_fish(cmd, env=env, interactive=True)
    assert cached.returncode == 0, cached.stderr
    assert cached.stderr == "", cached.stderr
    assert cached.stdout.strip() == "mise=live atuin=live fzf=live starship=live zoxide=live"
    assert not calls.exists()

    # Touching a binary invalidates only its cached init script.
    future = time.time() + 10
    os.utime(bin_dir / "fzf", (future, future))
    refreshed = _run_fish(cmd, env=env, interactive=True)
    assert refreshed.returncode == 0, refreshed.stderr
    assert refreshed.stdout.strip() == "mise=live atuin=live fzf=live starship=live zoxide=live"
    assert calls.read_text(encoding="utf-8").splitlines() == ["fzf --fish"]

    # An in-place upgrade whose archive preserves an older mtime still invalidates the cache.
    calls.unlink()
    older = time.time() - 3600
    os.utime(bin_dir / "zoxide", (older, older))
    older_refresh = _run_fish(cmd, env=env, interactive=True)
    assert older_refresh.returncode == 0, older_refresh.stderr
    assert calls.read_text(encoding="utf-8").splitlines() == ["zoxide init fish"]

    # Empty tool output never commits a header-only no-op cache file.
    empty_env = _clean_fish_env(tmp_path / "empty", PLUGIN_TEST_CALLS=str(tmp_path / "empty-calls"), ZELLIJ="0")
    empty_bin = tmp_path / "empty-bin"
    empty_bin.mkdir()
    for name in ("mise", "fzf", "atuin", "starship", "zoxide"):
        exe = empty_bin / name
        exe.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        exe.chmod(0o755)
    empty_run = _run_fish(
        f'set -gx PATH "{empty_bin}" $PATH; source dot_config/fish/conf.d/plugins.fish',
        env=empty_env,
        interactive=True,
    )
    assert empty_run.returncode == 0, empty_run.stderr
    assert not list((tmp_path / "empty/.cache/fish/init").glob("*.fish"))

    # Relative XDG_CACHE_HOME is ignored per XDG spec and falls back to $HOME/.cache.
    rel_home = tmp_path / "rel-home"
    rel_home.mkdir()
    rel_cwd = tmp_path / "untrusted-cwd"
    (rel_cwd / "relcache/fish/init").mkdir(parents=True)
    (rel_cwd / "relcache/fish/init/mise.fish").write_text("set -g stub_mise poisoned\n", encoding="utf-8")
    rel_env = _clean_fish_env(
        rel_home, XDG_CACHE_HOME="relcache", PLUGIN_TEST_CALLS=str(tmp_path / "rel-calls"), ZELLIJ="0"
    )
    rel_cmd = cmd.replace("dot_config/fish/conf.d/plugins.fish", f'"{ROOT / "dot_config/fish/conf.d/plugins.fish"}"')
    rel_run = _run_fish(rel_cmd, cwd=rel_cwd, env=rel_env, interactive=True)
    assert rel_run.returncode == 0, rel_run.stderr
    assert rel_run.stdout.strip() == "mise=live atuin=live fzf=live starship=live zoxide=live"
    assert (rel_home / ".cache/fish/init/mise.fish").is_file()

    # Unreadable cache file and read-only cache dir both fall back cleanly without stderr errors.
    if os.geteuid() != 0:
        unreadable_cache = rel_home / ".cache/fish/init/mise.fish"
        unreadable_cache.chmod(0o000)
        cache_dir = rel_home / ".cache/fish/init"
        cache_dir.chmod(0o500)
        try:
            fallback_run = _run_fish(rel_cmd, cwd=rel_cwd, env=rel_env, interactive=True)
            assert fallback_run.returncode == 0, fallback_run.stderr
            assert fallback_run.stderr == "", fallback_run.stderr
            assert fallback_run.stdout.strip() == "mise=live atuin=live fzf=live starship=live zoxide=live"
        finally:
            cache_dir.chmod(0o700)
            unreadable_cache.chmod(0o600)


def test_config_fish_skips_unsafe_private_fish_without_errors(tmp_path: Path) -> None:
    base_cmd = "source dot_config/fish/config.fish"
    env = _clean_fish_env(tmp_path, ZELLIJ="0", TERM_PROGRAM="ghostty")

    # Non-regular or unreadable or symlinked ~/.private.fish is skipped cleanly without stderr errors.
    private_fish = tmp_path / ".private.fish"
    private_target = tmp_path / "private-target.fish"
    private_target.write_text("set -gx SYM_PRIVATE_SOURCED 1\n", encoding="utf-8")
    private_fish.symlink_to(private_target)
    rc_sym, stdout_sym, stderr_sym = _run_fish_pty(
        f'{base_cmd}; if set -q SYM_PRIVATE_SOURCED; echo "SYM=1"; else; echo "SYM=0"; end',
        cwd=ROOT,
        env=env,
    )
    assert rc_sym == 0
    assert stderr_sym == "", stderr_sym
    assert stdout_sym.splitlines() == ["SYM=0"]
    private_fish.unlink()
    private_target.unlink()

    private_fish.mkdir()
    rc_dir, _stdout_dir, stderr_dir = _run_fish_pty(base_cmd, cwd=ROOT, env=env)
    assert rc_dir == 0
    assert stderr_dir == "", stderr_dir
    private_fish.rmdir()

    # A regular 0600 ~/.private.fish IS sourced cleanly.
    private_fish.write_text("set -gx PRIVATE_OK loaded\n", encoding="utf-8")
    private_fish.chmod(0o600)
    rc_ok, stdout_ok, stderr_ok = _run_fish_pty(f'{base_cmd}; printf "OK=%s\\n" "$PRIVATE_OK"', cwd=ROOT, env=env)
    assert rc_ok == 0
    assert stderr_ok == "", stderr_ok
    assert stdout_ok.splitlines() == ["OK=loaded"]
    private_fish.unlink()

    if os.geteuid() != 0:
        private_fish.write_text("set -gx SECRET_STUFF 1\n", encoding="utf-8")
        private_fish.chmod(0o000)
        try:
            rc_perm, _stdout_perm, stderr_perm = _run_fish_pty(base_cmd, cwd=ROOT, env=env)
            assert rc_perm == 0
            assert stderr_perm == "", stderr_perm
        finally:
            private_fish.chmod(0o600)
            private_fish.unlink()


def test_theme_fish_loads_fmind_colors_without_errors(tmp_path: Path) -> None:
    themes_dir = tmp_path / ".config/fish/themes"
    themes_dir.mkdir(parents=True)
    theme_file = themes_dir / "fmind.theme"
    theme_file.write_text(
        "# comment\n"
        "\n"
        "fish_color_command 174ea6\n"
        "fish_color_keyword 174ea6 --bold\n"
        "fish_color_valid_path --underline\n"
        "fish_pager_color_background --background=ffffff\n",
        encoding="utf-8",
    )
    env = _clean_fish_env(tmp_path, XDG_CONFIG_HOME=str(tmp_path / ".config"))
    theme_cmd = (
        "source dot_config/fish/conf.d/theme.fish; "
        'printf "cmd=%s\\nkw=%s\\n" '
        "(string join , -- $fish_color_command) "
        "(string join , -- $fish_color_keyword)"
    )
    result = _run_fish(theme_cmd, env=env, interactive=True)
    assert result.returncode == 0, result.stderr
    assert result.stderr == "", result.stderr
    assert result.stdout.splitlines() == ["cmd=174ea6,--theme=fmind", "kw=174ea6,--bold,--theme=fmind"]

    # A second interactive shell reuses the cached theme script and preserves the exact colors.
    cached_theme = _run_fish(theme_cmd, env=env, interactive=True)
    assert cached_theme.returncode == 0, cached_theme.stderr
    assert cached_theme.stderr == "", cached_theme.stderr
    assert cached_theme.stdout.splitlines() == ["cmd=174ea6,--theme=fmind", "kw=174ea6,--bold,--theme=fmind"]
    theme_cache = tmp_path / ".cache/fish/theme-fmind.fish"
    assert len(theme_cache.read_text(encoding="utf-8").splitlines()[0].split("|")) == 3

    if os.geteuid() != 0:
        theme_cache.chmod(0o000)
        try:
            unreadable_cache_run = _run_fish(theme_cmd, env=env, interactive=True)
            assert unreadable_cache_run.returncode == 0, unreadable_cache_run.stderr
            assert unreadable_cache_run.stderr == "", unreadable_cache_run.stderr
            assert unreadable_cache_run.stdout.splitlines() == [
                "cmd=174ea6,--theme=fmind",
                "kw=174ea6,--bold,--theme=fmind",
            ]
        finally:
            theme_cache.chmod(0o600)

    # Missing or unreadable fmind.theme is skipped cleanly without stderr errors.
    theme_file.unlink()
    missing_run = _run_fish("source dot_config/fish/conf.d/theme.fish", env=env, interactive=True)
    assert missing_run.returncode == 0, missing_run.stderr
    assert missing_run.stderr == "", missing_run.stderr

    if os.geteuid() != 0:
        theme_file.write_text("fish_color_command 174ea6\n", encoding="utf-8")
        theme_file.chmod(0o000)
        try:
            perm_run = _run_fish("source dot_config/fish/conf.d/theme.fish", env=env, interactive=True)
            assert perm_run.returncode == 0, perm_run.stderr
            assert perm_run.stderr == "", perm_run.stderr
        finally:
            theme_file.chmod(0o600)


def test_fish_env_exports_stay_mirrored_in_mise_config(tmp_path: Path) -> None:
    base_mise_env = {
        key: str(value).replace("{{env.HOME}}", str(tmp_path))
        for key, value in tomllib.loads((ROOT / "dot_config/mise/config.toml").read_text(encoding="utf-8"))[
            "env"
        ].items()
    }
    macos_mise_env = {
        key: str(value).replace("{{env.HOME}}", str(tmp_path))
        for key, value in tomllib.loads((ROOT / "dot_config/mise/conf.d/macos.toml").read_text(encoding="utf-8"))[
            "env"
        ].items()
    }
    assert "GOOGLE_WORKSPACE_CLI_KEYRING_BACKEND" not in base_mise_env
    assert macos_mise_env == {"GOOGLE_WORKSPACE_CLI_KEYRING_BACKEND": "file"}
    assert ".config/mise/conf.d/macos.toml" in (ROOT / ".chezmoiignore").read_text(encoding="utf-8")

    def _exported(path_env: str) -> dict[str, str]:
        base_env = {"HOME": str(tmp_path), "PATH": path_env}
        baseline = _run_fish("env -0", env=base_env, timeout=10, check=True)
        sourced = _run_fish("source dot_config/fish/conf.d/env.fish; env -0", env=base_env, timeout=10, check=True)
        before = dict(entry.split("=", 1) for entry in baseline.stdout.split("\0") if "=" in entry)
        after = dict(entry.split("=", 1) for entry in sourced.stdout.split("\0") if "=" in entry)
        return {key: value for key, value in after.items() if before.get(key) != value and key not in SHELL_ONLY_ENV}

    expected_native = base_mise_env | (macos_mise_env if sys.platform == "darwin" else {})
    assert _exported("/usr/bin:/bin") == expected_native

    # Exercise both OS branches via a synthetic uname shim so Linux CI covers macOS-only exports too.
    for os_name, expected in (("Linux", base_mise_env), ("Darwin", base_mise_env | macos_mise_env)):
        shim_dir = tmp_path / f"bin-{os_name}"
        shim_dir.mkdir()
        uname_shim = shim_dir / "uname"
        uname_shim.write_text(f"#!/bin/sh\necho {os_name}\n", encoding="utf-8")
        uname_shim.chmod(0o755)
        assert _exported(f"{shim_dir}:/usr/bin:/bin") == expected


def test_fish_env_repairs_broken_shell_and_preserves_valid_login_shell(tmp_path: Path) -> None:
    repaired = _run_fish(
        "source dot_config/fish/conf.d/env.fish; printf '%s' $SHELL",
        env={"HOME": str(tmp_path), "PATH": "/usr/bin:/bin", "SHELL": str(tmp_path / "missing-fish")},
        timeout=10,
        check=True,
    )
    assert Path(repaired.stdout).is_file()
    assert os.access(repaired.stdout, os.X_OK)

    preserved = _run_fish(
        "source dot_config/fish/conf.d/env.fish; printf '%s' $SHELL",
        env={"HOME": str(tmp_path), "PATH": "/usr/bin:/bin", "SHELL": "/bin/sh"},
        timeout=10,
        check=True,
    )
    assert preserved.stdout == "/bin/sh"


def test_agy_wrapper_isolates_mise_installs_and_preserves_parent_shell(tmp_path: Path) -> None:
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
        'printf "GIT_TERMINAL_PROMPT=%s\\n" "${GIT_TERMINAL_PROMPT:-unset}"\n'
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
    result = _run_fish(
        script,
        env={"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"},
        interactive=True,
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
    assert lines["GIT_TERMINAL_PROMPT"] == "0"
    assert lines["GH_PROMPT_DISABLED"] == "1"
    assert lines["CLOUDSDK_CORE_DISABLE_PROMPTS"] == "1"
    assert lines["ARGS"] == "--version"
    assert str(installs) in lines["AFTER_PATH"].split(":")
    assert lines["AFTER_MISE_SHELL"] == "fish"


def test_shell_secret_exports_are_retired() -> None:
    conf = ROOT / "dot_config/fish/conf.d"
    assert not any((conf / name).exists() for name in ("secrets.fish", "private_secrets.fish"))
    # Any `set` that exports (-x, -gx, -g -x, --export) a token-like name is a regression.
    export = re.compile(r"\bset\s+(?:-{1,2}\w+\s+)*?(?:-\w*x\w*|--export)\s+(?:-{1,2}\w+\s+)*\w*(TOKEN|API_KEY)")
    for script in (ROOT / "dot_config/fish").rglob("*.fish*"):
        assert not export.search(script.read_text(encoding="utf-8")), script


def test_with_secret_injects_only_child_process_and_fails_closed(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    wrapper = bin_dir / "with-secret"
    wrapper.write_text(
        f"#!{sys.executable}\n"
        f"import sys; sys.path.insert(0, {str(ROOT / 'dot/src')!r})\n"
        "from fmind_dot.with_secret import main; main()\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)

    secrets = tmp_path / ".config/dot/secrets"
    secrets.mkdir(parents=True, mode=0o700)
    secret = secrets / "TEST_API_KEY"
    secret.write_text("synthetic-personal\n", encoding="utf-8")
    secret.chmod(0o600)
    other = secrets / "OTHER_API_KEY"
    other.write_text("other-secret\n", encoding="utf-8")
    other.chmod(0o400)

    base_env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"TEST_API_KEY", "OTHER_API_KEY", "UV_PUBLISH_TOKEN", "DOT_CONFIG_PATH"}
    } | {"HOME": str(tmp_path), "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}

    py = sys.executable
    nested = _run_fish(
        f"with-secret TEST_API_KEY -- with-secret OTHER_API_KEY -- {py} -c "
        '\'import os,sys; print(os.environ["TEST_API_KEY"]); print(os.environ["OTHER_API_KEY"]); print(sys.argv[1:])\' '
        "'a b' '$(touch nope)'; not set -q TEST_API_KEY; and not set -q OTHER_API_KEY",
        env=base_env,
    )
    assert nested.returncode == 0, nested.stderr
    assert nested.stdout.splitlines() == ["synthetic-personal", "other-secret", "['a b', '$(touch nope)']"]
    assert not (ROOT / "nope").exists()

    posix_shell = subprocess.run(
        ["/bin/sh", "-c", f'with-secret TEST_API_KEY -- "{py}" -c \'import os; print(os.environ["TEST_API_KEY"])\''],
        cwd=ROOT,
        env=base_env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        check=False,
    )
    assert posix_shell.returncode == 0, posix_shell.stderr
    assert posix_shell.stdout.strip() == "synthetic-personal"
