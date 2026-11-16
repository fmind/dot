from __future__ import annotations

import json
from pathlib import Path

import pytest

from dot_tasks import completions as completions_module
from dot_tasks.completions import run_completion
from fmind_dot import auth as auth_module
from fmind_dot import system as system_module
from fmind_dot.archive.store import SESSION_PARSER_VERSION, SESSION_STORE_VERSION
from fmind_dot.archive.sync import SYNC_STATE_NAME, SYNC_STATE_SCHEMA
from fmind_dot.cli import app
from fmind_dot.config import WORKSPACE_APIS, AuthConfig, Config
from fmind_dot.errors import CommandTimeoutError, DotError, UsageError
from fmind_dot.process import CommandResult
from fmind_dot.system import available_memory_bytes, headroom_results, run_doctor
from tests.fakes import CliRunner, ScriptedRunner, buf, doctor_sections, make_state


def test_run_completion_check_install_pruning_and_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(completions_module, "COMPLETION_TOOLS", ("dot", "uv", "missing"))
    monkeypatch.setattr(completions_module, "MANAGED_COMPLETIONS", ("custom.fish",))
    comp_dir = tmp_path / ".config/fish/completions"
    cache_dir = tmp_path / ".cache/fish"
    comp_dir.mkdir(parents=True)
    cache_dir.mkdir(parents=True)
    (comp_dir / "stale.fish").write_text("# stale")
    (comp_dir / "custom.fish").write_text("# keep")
    (cache_dir / "old-init.fish").write_text("# stale init")

    runner = ScriptedRunner(
        {"uv", "fish", "atuin"},
        run=lambda *_a: CommandResult("complete -c uv\n", "", 0),
    )
    run_completion(make_state(runner), check_only=True)
    assert (comp_dir / "stale.fish").exists()

    run_completion(make_state(runner))
    assert (comp_dir / "dot.fish").is_file()
    assert (comp_dir / "uv.fish").is_file()
    assert not (comp_dir / "stale.fish").exists()
    assert (comp_dir / "custom.fish").exists()
    assert (cache_dir / "atuin-init.fish").is_file()
    assert not (cache_dir / "old-init.fish").exists()

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
    mise_bin.write_text("#!/bin/sh\n")
    lsd_dir = tmp_path / "pkgs/lsd"
    (lsd_dir / "completions").mkdir(parents=True)
    (lsd_dir / "completions/lsd.fish").write_text("complete -c lsd\n")
    hyperfine_dir = tmp_path / "pkgs/hyperfine"
    hyperfine_dir.mkdir(parents=True)
    cliff_dir = tmp_path / "pkgs/git-cliff"
    cliff_dir.mkdir(parents=True)
    (cliff_dir / "git-cliff.fish").write_bytes(b"\xff\xfe")

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
        if cmd == ["mise", "where", "--", "hyperfine"]:
            return CommandResult(f"{hyperfine_dir}\n", "", 0)
        if cmd == ["mise", "where", "--", "git-cliff"]:
            return CommandResult(f"{cliff_dir}\n", "", 0)
        if cmd[0] == "uv":
            return CommandResult("   \n", "", 0)
        if cmd[0] == "gh":
            return CommandResult("", "err", 1)
        if cmd[0] == "atuin":
            return CommandResult("\n", "", 0)
        return CommandResult("complete -c tool\n", "", 0)

    monkeypatch.setattr(
        completions_module,
        "COMPLETION_TOOLS",
        ("rg", "fd", "bat", "lsd", "zoxide", "hyperfine", "git-cliff", "hf", "git-lfs", "uv", "gh"),
    )
    runner = ShimRunner(
        {"fish", "env", "lsd", "zoxide", "hyperfine", "git-cliff", "hf", "git-lfs", "uv", "gh", "atuin"}, run=handle_run
    )
    with pytest.raises(DotError) as exc_info:
        run_completion(make_state(runner), check_only=True)
    message = str(exc_info.value)
    assert "rg:" not in message
    assert "failed to resolve mise completion executable for fd" in message
    assert "bat:" not in message
    assert ["bat", "--completion", "fish"] in runner.calls
    assert "lsd:" not in message
    assert ["env", "_HF_COMPLETE=fish_source", "hf"] in runner.calls
    assert "hf:" not in message
    assert "invalid completion package directory for zoxide" in message
    assert "expected one bundled Fish completion for hyperfine, found 0" in message
    assert "bundled Fish completion for git-cliff is not UTF-8" in message
    assert "completion generator for git-lfs is not installed: git" in message
    assert "failed to generate completions for uv: empty output" in message
    assert "failed to generate completions for gh" in message
    assert "atuin-init.fish: generated Fish script is empty: atuin-init.fish" in message

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


def test_secrets_tools_docker_install_and_headroom(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(system_module, "DOCTOR_TOOLS", ("git", "broken", "missing", "timed"))
    monkeypatch.setattr(system_module, "DOCTOR_SECRETS", ("~/.ssh/id_ed25519_signing", "~/.private.env"))
    (tmp_path / ".ssh").mkdir()
    key = tmp_path / ".ssh/id_ed25519_signing"
    key.write_text("k")
    key.chmod(0o644)
    (tmp_path / ".private.fish").symlink_to(tmp_path / "outside")

    def fake_run(cmd: list[str], *_a: object) -> CommandResult:
        name = Path(cmd[0]).name
        if name == "timed":
            raise CommandTimeoutError("timed")
        if name == "broken":
            return CommandResult("", "err", 1)
        if name == "docker":
            return CommandResult("", "stopped", 1)
        if cmd[:2] == ["chezmoi", "source-path"]:
            return CommandResult(str(tmp_path / "src") + "\n", "", 0)
        return CommandResult("ok\n", "", 0)

    src = tmp_path / "src/dot"
    (src / "src/fmind_dot").mkdir(parents=True)
    (src / "pyproject.toml").write_text('[project]\nversion = "0.0.0"\n')
    monkeypatch.setattr(system_module, "PACKAGE_DIRECTORY", tmp_path / "site-packages/fmind_dot")
    monkeypatch.setattr(system_module, "__version__", "1.0.0")
    st = make_state(ScriptedRunner({"git", "broken", "timed", "docker", "chezmoi"}, run=fake_run))
    sec = doctor_sections(run_doctor(st, fix=True))
    assert key.stat().st_mode & 0o777 == 0o600
    assert {r["name"]: r["status"] for r in sec["secrets"]}["~/.ssh/id_ed25519_signing.pub"] == "warn"
    assert {r["name"]: r["status"] for r in sec["secrets"]}["~/.private.fish"] == "fail"
    assert {r["name"]: r["status"] for r in sec["tools"]} == {
        "git": "pass",
        "broken": "fail",
        "missing": "fail",
        "timed": "fail",
    }
    assert sec["docker"][0]["status"] == "warn"
    assert sec["install"][0]["condition"] == "stale"

    (src / "pyproject.toml").write_text('[project]\nversion = "1.0.0"\n')
    assert system_module._install_results(st)[0].status == "pass"  # noqa: SLF001

    mem = tmp_path / "meminfo"
    mem.write_text("MemTotal: 1000 kB\nMemAvailable: 8388608 kB\n")
    assert available_memory_bytes(mem) == 8388608 * 1024
    hr = headroom_results([tmp_path, tmp_path / "missing"], memory=512 * 1024**2)
    assert {r.name: r.status for r in hr}["memory"] == "fail"


def test_doctor_agents_deep_auth_and_cli_options(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(system_module, "DOCTOR_TOOLS", ("git",))
    monkeypatch.setattr(system_module, "DOCTOR_SECRETS", ())
    shared = tmp_path / ".agents/skills"
    (shared / "s").mkdir(parents=True)
    (shared / "s/SKILL.md").write_text("---\nname: s\ndescription: s\nlicense: MIT\n---\n")
    (tmp_path / ".agents/AGENTS.md").write_text("# P\n")
    for p, sk in system_module._AGENT_HOSTS.values():  # noqa: SLF001
        pp = system_module.expand_path(p)
        pp.parent.mkdir(parents=True, exist_ok=True)
        pp.symlink_to(tmp_path / ".agents/AGENTS.md")
        if sk:
            sp = system_module.expand_path(sk)
            sp.parent.mkdir(parents=True, exist_ok=True)
            sp.symlink_to(shared)
    root = tmp_path / ".agents/sessions" / SESSION_STORE_VERSION
    for agent in ("agy", "claude", "pi"):
        (root / agent).mkdir(parents=True)
        (root / agent / SYNC_STATE_NAME).write_text(
            json.dumps(
                {
                    "schema": SYNC_STATE_SCHEMA,
                    "synced_at": "2026-11-15T00:00:00Z",
                    "failed": 0,
                    "retained": 0,
                    "parser_version": SESSION_PARSER_VERSION,
                }
            )
        )

    def auth_run(cmd: list[str], *_a: object) -> CommandResult:
        if cmd[0] == "gh":
            return CommandResult(
                json.dumps(
                    {
                        "hosts": {
                            "github.com": [
                                {
                                    "active": True,
                                    "state": "success",
                                    "scopes": "repo, workflow",
                                    "tokenSource": "/x/hosts.yml",
                                }
                            ]
                        }
                    }
                ),
                "",
                0,
            )
        if cmd[0] == "gcloud" and "application-default" in cmd:
            raise CommandTimeoutError("timeout")
        if cmd[0] == "gcloud":
            return CommandResult("tok\n", "", 0)
        return CommandResult("ok\n", "", 0)

    cfg = Config(auth=AuthConfig(login=["github", "gcp"]))
    st = make_state(ScriptedRunner({"git", "gh", "gcloud"}, run=auth_run), cfg)
    sec = doctor_sections(run_doctor(st, fix=False, deep=True))
    assert {a["name"] for a in sec["agents"]} == {"agy", "claude", "pi"}
    assert all(a["status"] == "pass" for a in sec["agents"])
    assert {r["name"]: r["status"] for r in sec["auth"]} == {
        "gh": "warn",
        "gcloud": "pass",
        "gcloud-adc": "fail",
        "gws": "skip",
    }

    res = CliRunner().invoke(app, ["doctor", "--headroom", "--json"])
    assert res.exit_code in {0, 1}
    assert json.loads(res.stdout)["scope"] == "headroom"
    txt = CliRunner().invoke(app, ["doctor", "--headroom"])
    assert "headroom:" in txt.stdout
    bad = CliRunner().invoke(app, ["doctor", "--headroom", "--fix"])
    assert bad.exit_code == 2


def test_probe_json_github_and_gcp_and_colab_login_flows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    st = make_state(ScriptedRunner({"gcloud"}, run=lambda *_a: CommandResult("", "Reauthentication required", 1)))
    with pytest.raises(DotError, match="run dot login gcp"):
        auth_module.probe_json(st, ["gcloud", "x"])

    with pytest.raises(DotError, match="github authentication state is unknown"):
        auth_module.github_entry({"hosts": {"github.com": [{"active": True, "state": "error", "error": "boom"}]}})
    assert (
        auth_module.github_entry({"hosts": {"github.com": [{"active": True, "state": "error", "error": "(HTTP 401)"}]}})
        is None
    )

    st_dry = make_state(ScriptedRunner({"gh"}))
    auth_module.login_github(st_dry, dry_run=True, grants=["read:org"])
    assert "--web" in buf(st_dry.stdout)
    assert "--remove-scopes" not in buf(st_dry.stdout)

    monkeypatch.setenv("GH_TOKEN", "tok")
    with pytest.raises(DotError, match="environment token"):
        auth_module.login_github(make_state(ScriptedRunner({"gh"})), force=True)
    monkeypatch.delenv("GH_TOKEN")

    gh_calls: list[str] = []
    entry_ok = {"active": True, "state": "success", "scopes": ", ".join(auth_module.GITHUB_SCOPES)}
    gh_runner = ScriptedRunner(
        {"gh"},
        run=lambda *_a: CommandResult(json.dumps({"hosts": {"github.com": [entry_ok] if gh_calls else []}}), "", 0),
    )
    monkeypatch.setattr(gh_runner, "interactive", lambda args, **_k: (gh_calls.append(" ".join(args)), 0)[1])
    st_gh = make_state(gh_runner)
    auth_module.login_github(st_gh)
    assert len(gh_calls) == 2

    st_gcp_dry = make_state()
    auth_module.login_gcp(st_gcp_dry, dry_run=True)
    assert "application-default login" in buf(st_gcp_dry.stdout)

    gcp_runner = ScriptedRunner(
        {"gcloud"},
        responses={
            ("gcloud", "auth", "print-access-token"): [
                CommandResult("", "Reauthentication", 1),
                CommandResult("t\n", "", 0),
            ]
        },
    )
    auth_module.login_gcp(make_state(gcp_runner))
    assert any("login" in c for c in gcp_runner.calls)

    colab_r = ScriptedRunner(
        {"gcloud", "colab"},
        run=lambda cmd, *_a: (
            CommandResult("", "DefaultCredentialsError", 1) if cmd[0] == "colab" else CommandResult("t\n", "", 0)
        ),
    )
    assert auth_module.colab_ready(make_state(colab_r)) is False
    with pytest.raises(DotError, match="Colab login did not provide"):
        auth_module.login_colab(make_state(colab_r))
    ok_colab = ScriptedRunner({"gcloud", "colab"}, run=lambda *_a: CommandResult("sess\n", "", 0))
    st_colab = make_state(ok_colab)
    auth_module.login_colab(st_colab)
    assert auth_module.COLAB_SESSIONS in ok_colab.calls


def test_workspace_login_machine_and_check_cli_guards(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("GWS_PROJECT", raising=False)
    gws_dir = tmp_path / ".config/gws"
    gws_dir.mkdir(parents=True)
    (gws_dir / "token_cache.json").write_text("{}")

    cfg = Config(auth=AuthConfig(login=["gcp", "workspace", "colab"]))
    cfg.auth.workspace.project = "my-proj-1"
    status_seq = [
        CommandResult(json.dumps({"client_config_exists": False, "enabled_apis": []}), "", 0),
        CommandResult(
            json.dumps(
                {
                    "client_config_exists": True,
                    "project_id": "my-proj-1",
                    "enabled_apis": ["drive.googleapis.com"],
                    "auth_method": "none",
                }
            ),
            "",
            0,
        ),
        CommandResult(
            json.dumps(
                {
                    "token_valid": True,
                    "scopes": [*cfg.auth.workspace.scopes, "https://www.googleapis.com/auth/chat.spaces.create"],
                }
            ),
            "",
            0,
        ),
    ]
    runner = ScriptedRunner({"gcloud", "gws", "colab"}, responses={("gws", "auth", "status"): status_seq})
    st = make_state(runner, cfg)
    auth_module.login_workspace(st, grants=["chat.spaces.create"])
    assert not (gws_dir / "token_cache.json").exists()
    assert "One-off Workspace scopes" in buf(st.stderr)
    enable_calls = [c for c in runner.calls if c[:3] == ["gcloud", "services", "enable"]]
    assert len(enable_calls) >= 2
    assert all(1 <= len(c[3:-3]) <= 20 for c in enable_calls)
    assert [api for c in enable_calls for api in c[3:-3]] == list(WORKSPACE_APIS)

    partial_runner = ScriptedRunner(
        {"gcloud", "gws"},
        responses={
            ("gws", "auth", "status"): [
                CommandResult(
                    json.dumps(
                        {
                            "client_config_exists": True,
                            "project_id": "my-proj-1",
                            "enabled_apis": list(WORKSPACE_APIS[:15]),
                        }
                    ),
                    "",
                    0,
                )
            ]
        },
    )
    auth_module.setup_workspace(make_state(partial_runner, cfg), "my-proj-1")
    partial_enables = [c[3:-3] for c in partial_runner.calls if c[:3] == ["gcloud", "services", "enable"]]
    assert all(len(batch) <= 20 for batch in partial_enables)
    assert [api for batch in partial_enables for api in batch] == list(WORKSPACE_APIS[15:])

    denied_err = "ERROR: (gcloud.services.enable) Permission denied to enable service [admin.googleapis.com] reason: AUTH_PERMISSION_DENIED"
    perm_runner = ScriptedRunner(
        {"gcloud", "gws"},
        run=lambda cmd, *_a: (
            CommandResult(
                json.dumps(
                    {
                        "client_config_exists": True,
                        "project_id": "my-proj-1",
                        "enabled_apis": ["drive.googleapis.com"],
                    }
                ),
                "",
                0,
            )
            if cmd[:3] == ["gws", "auth", "status"]
            else CommandResult("", denied_err, 1)
        ),
    )
    st_perm = make_state(perm_runner, cfg)
    auth_module.setup_workspace(st_perm, "my-proj-1")
    assert "using pre-enabled APIs" in buf(st_perm.stderr)

    unconfigured_runner = ScriptedRunner(
        {"gcloud", "gws"},
        run=lambda cmd, *_a: (
            CommandResult(json.dumps({"client_config_exists": False}), "", 0)
            if cmd[:3] == ["gws", "auth", "status"]
            else CommandResult("", denied_err, 1)
        ),
    )
    with pytest.raises(DotError, match="command failed"):
        auth_module.setup_workspace(make_state(unconfigured_runner, cfg), "my-proj-1")

    ready_runner = ScriptedRunner(
        {"gcloud", "gws"},
        responses={
            ("gws", "auth", "status"): [
                CommandResult(
                    json.dumps(
                        {
                            "client_config_exists": True,
                            "project_id": "my-proj-1",
                            "enabled_apis": [],
                            "token_valid": True,
                            "scopes": list(cfg.auth.workspace.scopes),
                        }
                    ),
                    "",
                    0,
                )
            ]
        },
    )
    st_ready = make_state(ready_runner, cfg)
    auth_module.login_workspace(st_ready, project="my-proj-1")
    assert ready_runner.calls == [["gws", "auth", "status"]]
    assert "already authenticated" in buf(st_ready.stderr)

    with pytest.raises(UsageError, match="invalid scope"):
        auth_module.one_off_scopes(["not valid!"], [])
    with pytest.raises(UsageError, match="PROJECT"):
        auth_module.login_workspace(make_state(runner, cfg), project="BAD", dry_run=True)

    st_chk = make_state(ScriptedRunner({"gh", "gcloud", "gws"}, run=lambda *_a: CommandResult("", "bad", 1)), cfg)
    with pytest.raises(SystemExit):
        auth_module.login_machine(st_chk, force=False, dry_run=False, check=True)
    assert "login needed" in buf(st_chk.stdout) or "unknown" in buf(st_chk.stdout)

    seen_colab_force: list[bool] = []
    monkeypatch.setattr(auth_module, "login_gcp", lambda *_a, **_k: None)
    monkeypatch.setattr(auth_module, "login_workspace", lambda *_a, **_k: None)
    monkeypatch.setattr(
        auth_module, "login_colab", lambda _s, *, force=False, dry_run=False: seen_colab_force.append(force or dry_run)
    )
    auth_module.login_machine(
        make_state(ScriptedRunner({"gcloud", "gws", "colab"}), cfg), force=True, dry_run=False, check=False
    )
    assert seen_colab_force == [False]

    monkeypatch.setattr("fmind_dot.state.State.config", cfg)
    for argv in (
        ["login", "--force", "gcp"],
        ["login", "gcp", "--check", "--force"],
        ["login", "github", "--check", "--grant", "repo"],
    ):
        assert CliRunner().invoke(app, argv).exit_code == 2
