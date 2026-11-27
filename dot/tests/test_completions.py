from __future__ import annotations

import json
from pathlib import Path

import pytest

from dot_tasks import completions as completions_module
from dot_tasks.completions import run_completion
from fmind_dot.errors import DotError
from fmind_dot.process import CommandResult
from tests.fakes import ScriptedRunner, make_state


def test_run_completion_check_install_pruning_and_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(completions_module, "COMPLETION_TOOLS", ("dot", "uv", "missing"))
    comp_dir = tmp_path / ".config/fish/completions"
    comp_dir.mkdir(parents=True)
    (comp_dir / "stale.fish").write_text("# stale", encoding="utf-8")

    runner = ScriptedRunner(
        {"uv", "fish"},
        run=lambda *_a: CommandResult("complete -c uv\n", "", 0),
    )
    run_completion(make_state(runner), check_only=True)
    assert (comp_dir / "stale.fish").exists()

    run_completion(make_state(runner))
    assert (comp_dir / "dot.fish").is_file()
    assert (comp_dir / "uv.fish").is_file()
    assert not (comp_dir / "stale.fish").exists()

    bad = ScriptedRunner(
        {"uv", "fish"},
        run=lambda cmd, *_a: CommandResult("", "syntax", 1) if cmd[0] == "fish" else CommandResult("bad", "", 0),
    )
    with pytest.raises(DotError, match="completion generation failed"):
        run_completion(make_state(bad), check_only=True)


def test_completion_packages_env_mise_shims_and_cli_main(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    mise_bin = tmp_path / "mise"
    mise_bin.write_text("#!/bin/sh\n", encoding="utf-8")
    lsd_dir = tmp_path / "pkgs/lsd"
    (lsd_dir / "completions").mkdir(parents=True)
    (lsd_dir / "completions/lsd.fish").write_text("complete -c lsd\n", encoding="utf-8")
    yazi_dir = tmp_path / "pkgs/yazi"
    yazi_dir.mkdir(parents=True)
    ya_dir = tmp_path / "pkgs/ya"
    ya_dir.mkdir(parents=True)
    (ya_dir / "ya.fish").write_bytes(b"\xff\xfe")

    class ShimRunner(ScriptedRunner):
        def which(self, command: str) -> Path | None:
            if command in {"mise", "rg", "fd", "bat"}:
                return mise_bin
            return super().which(command)

    def handle_run(cmd: list[str], *_a: object) -> CommandResult:
        if cmd == ["mise", "which", "rg"]:
            return CommandResult("", "rg is not currently active", 1)
        if cmd == ["mise", "which", "fd"]:
            return CommandResult("", "unexpected", 1)
        if cmd == ["mise", "which", "bat"]:
            return CommandResult("/opt/bat\n", "", 0)
        if cmd == ["mise", "where", "--", "lsd"]:
            return CommandResult(f"{lsd_dir}\n", "", 0)
        if cmd == ["mise", "where", "--", "zoxide"]:
            return CommandResult("relative/path\n", "", 0)
        if cmd == ["mise", "where", "--", "yazi"]:
            return CommandResult(f"{yazi_dir}\n", "", 0)
        if cmd == ["mise", "where", "--", "ya"]:
            return CommandResult(f"{ya_dir}\n", "", 0)
        if cmd[0] == "uv":
            return CommandResult("   \n", "", 0)
        if cmd[0] == "gh":
            return CommandResult("", "err", 1)
        return CommandResult("complete -c tool\n", "", 0)

    monkeypatch.setattr(
        completions_module,
        "COMPLETION_TOOLS",
        ("rg", "fd", "bat", "lsd", "zoxide", "yazi", "ya", "hf", "git-lfs", "uv", "gh", "lazygit"),
    )
    monkeypatch.setitem(completions_module._COMPLETION_PACKAGES, "ya", "ya")  # noqa: SLF001
    runner = ShimRunner(
        {"fish", "env", "lsd", "zoxide", "yazi", "ya", "hf", "git-lfs", "uv", "gh", "lazygit"}, run=handle_run
    )
    with pytest.raises(DotError) as exc_info:
        run_completion(make_state(runner), check_only=True)
    message = str(exc_info.value)
    assert "rg:" not in message
    assert "failed to resolve mise completion executable for fd" in message
    assert "bat:" not in message
    assert ["bat", "--completion", "fish"] in runner.calls
    assert ["lazygit", "completion", "fish"] in runner.calls
    assert "lazygit" in completions_module._PLAIN_COMPLETIONS  # noqa: SLF001
    assert "lazygit" not in completions_module._COMPLETION_COMMANDS  # noqa: SLF001
    assert "lsd:" not in message
    assert ["env", "_HF_COMPLETE=fish_source", "hf"] in runner.calls
    assert "hf:" not in message
    assert "invalid completion package directory for zoxide" in message
    assert "expected one bundled Fish completion for yazi, found 0" in message
    assert "bundled Fish completion for ya is not UTF-8" in message
    assert "completion generator for git-lfs is not installed: git" in message
    assert "failed to generate completions for uv: empty output" in message
    assert "failed to generate completions for gh" in message

    monkeypatch.setattr(completions_module, "COMPLETION_TOOLS", ("uv",))
    monkeypatch.setattr(
        completions_module,
        "State",
        lambda: make_state(ScriptedRunner({"uv", "fish"}, run=lambda *_a: CommandResult("complete -c uv\n", "", 0))),
    )
    assert completions_module.main(["--check"]) == 0

    monkeypatch.setattr(
        completions_module,
        "State",
        lambda: make_state(
            ScriptedRunner(
                {"uv", "fish"},
                run=lambda cmd, *_a: CommandResult("", "err", 1) if cmd[0] == "uv" else CommandResult("", "", 0),
            )
        ),
    )
    assert completions_module.main(["--check"]) == 1
    assert "completions: completion generation failed:" in capsys.readouterr().err


def test_completions_batched_mise_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    mise_bin = tmp_path / "bin/mise"
    mise_bin.parent.mkdir(parents=True)
    mise_bin.write_text("#!/bin/sh\n", encoding="utf-8")
    mise_bin.chmod(0o755)
    active_bin = tmp_path / "mise-bins"
    active_bin.mkdir()
    for tool in ("zoxide", "rg", "uv"):
        p = active_bin / tool
        p.write_text("#!/bin/sh\n", encoding="utf-8")
        p.chmod(0o755)
    zoxide_dir = tmp_path / "pkgs/zoxide"
    (zoxide_dir / "completions").mkdir(parents=True)
    (zoxide_dir / "completions/zoxide.fish").write_text("complete -c zoxide\n", encoding="utf-8")

    class BatchRunner(ScriptedRunner):
        def which(self, command: str) -> Path | None:
            if command in {"mise", "zoxide", "rg", "uv", "fd"}:
                return mise_bin
            return super().which(command)

    def handle_run(cmd: list[str], *_a: object) -> CommandResult:
        if cmd == ["mise", "ls", "--current", "--json"]:
            return CommandResult(
                json.dumps(
                    {
                        "zoxide": [{"active": True, "installed": True, "install_path": str(zoxide_dir)}],
                        "lsd": [{"active": False, "installed": True, "install_path": "/bad"}],
                    }
                ),
                "",
                0,
            )
        if cmd == ["mise", "bin-paths"]:
            return CommandResult(f"{active_bin}\n", "", 0)
        if cmd[:2] == ["mise", "which"] or cmd[:2] == ["mise", "where"]:
            raise AssertionError(f"unexpected unbatched mise call: {cmd}")
        return CommandResult("complete -c tool\n", "", 0)

    monkeypatch.setattr(completions_module, "COMPLETION_TOOLS", ("zoxide", "rg", "uv", "fd"))
    runner = BatchRunner({"fish"}, run=handle_run)
    run_completion(make_state(runner))
    comp_dir = tmp_path / ".config/fish/completions"
    assert (comp_dir / "zoxide.fish").is_file()
    assert (comp_dir / "rg.fish").is_file()
    assert (comp_dir / "uv.fish").is_file()
    assert not (comp_dir / "fd.fish").exists()
    uv_env = runner.envs[("uv", "generate-shell-completion", "fish")]
    assert uv_env is not None
    assert uv_env["PATH"].startswith(str(active_bin))
    fish_env = runner.envs[("fish", "--no-config", "--no-execute")]
    assert fish_env is not None
    assert fish_env["PATH"].startswith(str(active_bin))

    # _parse_install_paths handles malformed JSON, non-dict payloads, and inactive entries cleanly
    parse_paths = completions_module._parse_install_paths  # noqa: SLF001
    assert parse_paths("{not-json") == {}
    assert parse_paths("[]") == {}
    assert parse_paths(
        json.dumps(
            {
                "bad-entries": "not-a-list",
                "inactive": [{"active": False, "installed": True, "install_path": "/bad"}],
                "uninstalled": [{"active": True, "installed": False, "install_path": "/bad"}],
                "empty-path": [{"active": True, "installed": True, "install_path": ""}],
                "good": ["bad-entry", {"active": True, "installed": True, "install_path": "/ok/tool"}],
            }
        )
    ) == {"good": Path("/ok/tool")}
