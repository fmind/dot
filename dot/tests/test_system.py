from __future__ import annotations

import io
import json
import os
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from dot_tasks import completions as completions_module
from dot_tasks.completions import run_completion
from fmind_dot import auth as auth_module
from fmind_dot import auth_probes as auth_probes_module
from fmind_dot import system as system_module
from fmind_dot.cli import app
from fmind_dot.config import WORKSPACE_APIS, AuthConfig, Config
from fmind_dot.errors import CommandTimeoutError, DotError, UsageError
from fmind_dot.process import CommandResult
from fmind_dot.state import State
from fmind_dot.system import available_memory_bytes, headroom_results, run_doctor
from tests.fakes import CliRunner, ScriptedRunner, TerminalIO, buf, doctor_sections, make_state


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


def test_is_gce_vm_handles_non_utf8_dmi_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dmi = tmp_path / "product_name"
    dmi.write_bytes(b"\xff\xfeOEM Board\n")
    monkeypatch.setattr(auth_probes_module, "GCE_DMI_PRODUCT_PATH", dmi)
    assert auth_probes_module.is_gce_vm() is False
    dmi.write_bytes(b"\xffGoogle Compute Engine\n")
    assert auth_probes_module.is_gce_vm() is True


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
        if cmd[0] == "atuin":
            return CommandResult("\n", "", 0)
        return CommandResult("complete -c tool\n", "", 0)

    monkeypatch.setattr(
        completions_module,
        "COMPLETION_TOOLS",
        ("rg", "fd", "bat", "lsd", "zoxide", "yazi", "ya", "hf", "git-lfs", "uv", "gh"),
    )
    monkeypatch.setitem(completions_module._COMPLETION_PACKAGES, "ya", "ya")  # noqa: SLF001
    runner = ShimRunner({"fish", "env", "lsd", "zoxide", "yazi", "ya", "hf", "git-lfs", "uv", "gh"}, run=handle_run)
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


def test_secrets_tools_docker_install_and_headroom(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(system_module, "DOCTOR_TOOLS", ("git", "broken", "missing", "timed"))
    monkeypatch.setattr(system_module, "DOCTOR_SECRETS", ("~/.ssh/id_ed25519_signing", "~/.private.env"))
    (tmp_path / ".ssh").mkdir()
    key = tmp_path / ".ssh/id_ed25519_signing"
    key.write_text("k", encoding="utf-8")
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
    (src / "pyproject.toml").write_text('[project]\nversion = "0.0.0"\n', encoding="utf-8")
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

    (src / "pyproject.toml").write_text('[project]\nversion = "1.0.0"\n', encoding="utf-8")
    assert system_module._install_results(st)[0].status == "pass"  # noqa: SLF001

    mem = tmp_path / "meminfo"
    mem.write_text("MemTotal: 1000 kB\nMemAvailable: 8388608 kB\n", encoding="utf-8")
    assert available_memory_bytes(mem) == 8388608 * 1024
    hr = headroom_results([tmp_path, tmp_path / "missing"], memory=512 * 1024**2)
    assert {r.name: r.status for r in hr}["memory"] == "fail"


def test_doctor_agents_deep_auth_and_cli_options(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(system_module, "DOCTOR_TOOLS", ("git",))
    monkeypatch.setattr(system_module, "DOCTOR_SECRETS", ())
    shared = tmp_path / ".agents/skills"
    (shared / "s").mkdir(parents=True)
    (shared / "s/SKILL.md").write_text("---\nname: s\ndescription: s\nlicense: MIT\n---\n", encoding="utf-8")
    (tmp_path / ".agents/AGENTS.md").write_text("# P\n", encoding="utf-8")
    for p, sk in system_module._AGENT_HOSTS.values():  # noqa: SLF001
        pp = system_module.expand_path(p)
        pp.parent.mkdir(parents=True, exist_ok=True)
        pp.symlink_to(tmp_path / ".agents/AGENTS.md")
        if sk:
            sp = system_module.expand_path(sk)
            sp.parent.mkdir(parents=True, exist_ok=True)
            sp.symlink_to(shared)
    for rev_dir, rev_glob in system_module._AGENT_REVIEWERS.values():  # noqa: SLF001
        rd = system_module.expand_path(rev_dir)
        rd.mkdir(parents=True, exist_ok=True)
        (rd / rev_glob.replace("*", "code")).write_text("---\nname: fmind-review-code\n---\n", encoding="utf-8")

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
                                    "scopes": ", ".join(auth_module.GITHUB_SCOPES),
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
    assert {a["name"] for a in sec["agents"]} == {"agy", "copilot"}
    assert all(a["status"] == "pass" for a in sec["agents"])

    copilot_persona = system_module.expand_path(system_module._AGENT_HOSTS["copilot"][0])  # noqa: SLF001
    copilot_persona.unlink()
    broken_agents = {a["name"]: a for a in doctor_sections(run_doctor(st, fix=False))["agents"]}
    assert broken_agents["copilot"]["status"] == "fail"
    assert broken_agents["copilot"]["condition"] == "broken"
    assert broken_agents["agy"]["status"] == "pass"
    copilot_persona.symlink_to(tmp_path / ".agents/AGENTS.md")

    copilot_rev = system_module.expand_path(system_module._AGENT_REVIEWERS["copilot"][0])  # noqa: SLF001
    sample_rev = copilot_rev / "fmind-review-code.agent.md"
    sample_rev.unlink()
    missing_rev = {a["name"]: a for a in doctor_sections(run_doctor(st, fix=False))["agents"]}
    assert missing_rev["copilot"]["status"] == "fail"
    assert missing_rev["copilot"]["condition"] == "broken"
    assert "reviewers" in missing_rev["copilot"]["details"]
    sample_rev.write_text("---\nname: fmind-review-code\n---\n", encoding="utf-8")

    assert {r["name"]: r["status"] for r in sec["auth"]} == {
        "gh": "warn",
        "gcloud": "pass",
        "gcloud-adc": "fail",
        "gws": "skip",
    }

    monkeypatch.setattr(shutil, "disk_usage", lambda _p: SimpleNamespace(free=200 * 1024**3))
    monkeypatch.setattr(system_module, "available_memory_bytes", lambda: 8 * 1024**3)
    res_pass = CliRunner().invoke(app, ["doctor", "--headroom", "--json"])
    assert res_pass.exit_code == 0
    assert json.loads(res_pass.stdout)["scope"] == "headroom"
    txt_pass = CliRunner().invoke(app, ["doctor", "--headroom"])
    assert txt_pass.exit_code == 0
    assert "PASS · headroom:" in txt_pass.stdout

    monkeypatch.setattr(shutil, "disk_usage", lambda _p: SimpleNamespace(free=1 * 1024**3))
    monkeypatch.setattr(system_module, "available_memory_bytes", lambda: 0)
    res_fail = CliRunner().invoke(app, ["doctor", "--headroom"])
    assert res_fail.exit_code == 1
    assert "FAIL · headroom:" in res_fail.stdout
    bad = CliRunner().invoke(app, ["doctor", "--headroom", "--fix"])
    assert bad.exit_code == 2


def test_probe_json_github_and_gcp_login_flows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    st = make_state(ScriptedRunner({"gcloud"}, run=lambda *_a: CommandResult("", "Reauthentication required", 1)))
    with pytest.raises(DotError, match="run dot login gcp"):
        auth_probes_module.probe_json(st, ["gcloud", "x"])

    with pytest.raises(DotError, match="github authentication state is unknown"):
        auth_probes_module.github_entry(
            {"hosts": {"github.com": [{"active": True, "state": "error", "error": "boom"}]}}
        )
    assert (
        auth_probes_module.github_entry(
            {"hosts": {"github.com": [{"active": True, "state": "error", "error": "(HTTP 401)"}]}}
        )
        is None
    )

    st_dry = make_state(ScriptedRunner({"gh"}))
    auth_module.login_github(st_dry, dry_run=True, grants=["write:ssh_signing_key"])
    dry_out = buf(st_dry.stdout)
    assert "--web --clipboard" in dry_out
    assert "gh auth refresh" in dry_out
    assert "--remove-scopes admin:enterprise" in dry_out
    assert "delete_repo" not in dry_out
    with pytest.raises(UsageError, match="forbidden by security policy"):
        auth_module.login_github(make_state(ScriptedRunner({"gh"})), dry_run=True, grants=["admin:enterprise"])
    entry_forb = {
        "active": True,
        "state": "success",
        "scopes": ", ".join([*auth_module.GITHUB_SCOPES, "admin:enterprise"]),
    }
    assert auth_module.github_ready(entry_forb, reconcile=False) is False
    entry_disc = {
        "active": True,
        "state": "success",
        "scopes": ", ".join(s for s in [*auth_module.GITHUB_SCOPES, "write:discussion"] if s != "read:discussion"),
    }
    assert auth_module.github_ready(entry_disc, reconcile=True) is True

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
    assert len(gh_calls) == 1
    assert "--web --clipboard" in gh_calls[0]

    dirty_calls: list[str] = []
    entry_dirty = {"active": True, "state": "success", "scopes": ", ".join([*auth_module.GITHUB_SCOPES, "delete_repo"])}
    dirty_runner = ScriptedRunner(
        {"gh"},
        run=lambda *_a: CommandResult(
            json.dumps(
                {
                    "hosts": {
                        "github.com": [] if not dirty_calls else [entry_dirty] if len(dirty_calls) == 1 else [entry_ok]
                    }
                }
            ),
            "",
            0,
        ),
    )
    monkeypatch.setattr(dirty_runner, "interactive", lambda args, **_k: (dirty_calls.append(" ".join(args)), 0)[1])
    auth_module.login_github(make_state(dirty_runner))
    assert len(dirty_calls) == 2
    assert "--remove-scopes" in dirty_calls[1]

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


def test_workspace_login_machine_and_check_cli_guards(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("GWS_PROJECT", raising=False)
    gws_dir = tmp_path / ".config/gws"
    gws_dir.mkdir(parents=True)
    (gws_dir / "token_cache.json").write_text("{}", encoding="utf-8")

    cfg = Config(auth=AuthConfig(login=["gcp", "workspace"]))
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
                    "scopes": [*cfg.auth.workspace.scopes, "https://www.googleapis.com/auth/youtube.readonly"],
                }
            ),
            "",
            0,
        ),
    ]
    runner = ScriptedRunner({"gcloud", "gws"}, responses={("gws", "auth", "status"): status_seq})
    st = make_state(runner, cfg)
    auth_module.login_workspace(st, grants=["youtube.readonly"])
    assert not (gws_dir / "token_cache.json").exists()
    assert "One-off Workspace scopes" in buf(st.stderr)
    enable_calls = [c for c in runner.calls if c[:3] == ["gcloud", "services", "enable"]]
    assert len(enable_calls) == 1
    assert [api for c in enable_calls for api in c[3:-3]] == list(WORKSPACE_APIS)

    many_apis = tuple(f"svc{i}.googleapis.com" for i in range(25))
    monkeypatch.setattr(auth_module, "WORKSPACE_APIS", many_apis)
    batch_runner = ScriptedRunner(
        {"gcloud", "gws"},
        responses={
            ("gws", "auth", "status"): [
                CommandResult(
                    json.dumps({"client_config_exists": True, "project_id": "my-proj-1", "enabled_apis": []}), "", 0
                )
            ]
        },
    )
    auth_module.setup_workspace(make_state(batch_runner, cfg), "my-proj-1")
    batch_enables = [c[3:-3] for c in batch_runner.calls if c[:3] == ["gcloud", "services", "enable"]]
    assert len(batch_enables) == 2
    assert all(1 <= len(batch) <= 20 for batch in batch_enables)
    assert [api for batch in batch_enables for api in batch] == list(many_apis)
    monkeypatch.setattr(auth_module, "WORKSPACE_APIS", WORKSPACE_APIS)

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

    force_runner = ScriptedRunner(
        {"gws"},
        responses={
            ("gws", "auth", "status"): [
                CommandResult(
                    json.dumps(
                        {
                            "client_config_exists": True,
                            "project_id": "my-proj-1",
                            "enabled_apis": [],
                            "token_valid": True,
                        }
                    ),
                    "",
                    0,
                ),
                CommandResult(json.dumps({"token_valid": True, "scopes": list(cfg.auth.workspace.scopes)}), "", 0),
            ]
        },
    )
    auth_module.login_workspace(make_state(force_runner, cfg), force=True, project="my-proj-1")
    assert not any(c[:3] == ["gcloud", "services", "enable"] for c in force_runner.calls)

    forb_runner = ScriptedRunner(
        {"gws"},
        responses={
            ("gws", "auth", "status"): [
                CommandResult(
                    json.dumps(
                        {
                            "token_valid": True,
                            "scopes": [*cfg.auth.workspace.scopes, "https://www.googleapis.com/auth/cloud-platform"],
                        }
                    ),
                    "",
                    0,
                )
            ]
        },
    )
    assert auth_module.workspace_ready(make_state(forb_runner, cfg)) is False
    for bad_grant in ("cloud-platform", "https://mail.google.com", "HTTPS://MAIL.GOOGLE.COM/"):
        with pytest.raises(UsageError, match="forbidden by security policy"):
            auth_module.login_workspace(make_state(forb_runner, cfg), dry_run=True, grants=[bad_grant])
    with pytest.raises(UsageError, match="--setup requires a project ID"):
        auth_module.login_workspace(make_state(forb_runner), dry_run=True, setup=True)

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
        auth_probes_module.one_off_scopes(["not valid!"], [])
    for bad_grant in ("", "/", "-bad", "https://www.googleapis.com/auth/"):
        with pytest.raises(UsageError, match="invalid scope"):
            auth_module.login_workspace(make_state(runner, cfg), dry_run=True, grants=[bad_grant])
    with pytest.raises(UsageError, match="PROJECT"):
        auth_module.login_workspace(make_state(runner, cfg), project="BAD", dry_run=True)

    st_chk = make_state(ScriptedRunner({"gh", "gcloud", "gws"}, run=lambda *_a: CommandResult("", "bad", 1)), cfg)
    with pytest.raises(SystemExit):
        auth_module.login_machine(st_chk, force=False, dry_run=False, check=True)
    assert "login needed" in buf(st_chk.stdout) or "unknown" in buf(st_chk.stdout)

    seen_force: list[bool] = []
    with monkeypatch.context() as mp:
        mp.setattr(auth_module, "login_gcp", lambda _s, *, force=False, **_k: seen_force.append(force))
        mp.setattr(auth_module, "login_workspace", lambda *_a, **_k: None)
        auth_module.login_machine(
            make_state(ScriptedRunner({"gcloud", "gws"}), cfg), force=True, dry_run=False, check=False
        )
    assert seen_force == [True]

    monkeypatch.setattr("fmind_dot.state.State.config", cfg)
    # Verify --force/--dry-run/--check before provider behave identically to after provider.
    monkeypatch.setattr(
        "fmind_dot.cli.State",
        lambda **_kw: State(
            runner=ScriptedRunner({"gcloud"}, run=lambda *_a: CommandResult("tok\n", "", 0)),
        ),
    )
    assert CliRunner().invoke(app, ["login", "--check", "gcp"]).exit_code == 0
    assert "gcloud auth login" in CliRunner().invoke(app, ["login", "--force", "gcp", "--dry-run"]).stdout
    for argv in (
        ["login", "--force", "gcp", "--check"],
        ["login", "gcp", "--check", "--force"],
        ["login", "github", "--check", "--grant", "repo"],
        ["login", "workspace", "--check", "--setup"],
        ["login", "workspace", "--check", "--project", "bogus-project"],
        ["login", "--check", "workspace", "--project", "bogus-project"],
        ["login", "workspace", "--check", "--project", ""],
    ):
        res = CliRunner().invoke(app, argv)
        assert res.exit_code == 2
        if any(flag in argv for flag in ("--grant", "--project", "--setup")):
            assert "--check cannot be combined with --grant, --project, or --setup" in res.stderr


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
            if command in {"mise", "zoxide", "rg", "uv"}:
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
        if cmd == ["mise", "which", "rg"] or cmd[:2] == ["mise", "where"]:
            raise AssertionError(f"unexpected unbatched mise call: {cmd}")
        return CommandResult("complete -c tool\n", "", 0)

    monkeypatch.setattr(completions_module, "COMPLETION_TOOLS", ("zoxide", "rg", "uv"))
    runner = BatchRunner({"fish"}, run=handle_run)
    run_completion(make_state(runner))
    comp_dir = tmp_path / ".config/fish/completions"
    assert (comp_dir / "zoxide.fish").is_file()
    assert (comp_dir / "rg.fish").is_file()
    assert (comp_dir / "uv.fish").is_file()
    uv_env = runner.envs[("uv", "generate-shell-completion", "fish")]
    assert uv_env is not None
    assert uv_env["PATH"].startswith(str(active_bin))

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


def test_doctor_quiet_and_headroom_modes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(system_module, "DOCTOR_TOOLS", ("git", "broken"))
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
    for rev_dir, rev_glob in system_module._AGENT_REVIEWERS.values():  # noqa: SLF001
        rd = system_module.expand_path(rev_dir)
        rd.mkdir(parents=True, exist_ok=True)
        (rd / rev_glob.replace("*", "code")).write_text("---\nname: fmind-review-code\n---\n")

    assert system_module._inspect_agent("agy").status == "pass"  # noqa: SLF001
    assert system_module._inspect_agent("copilot").status == "pass"  # noqa: SLF001

    # CLI doctor output: default passing-tools collapse, -q text, -q --json, --headroom -q --json
    def doc_run(cmd: list[str], *_a: object) -> CommandResult:
        return CommandResult("", "err", 1) if Path(cmd[0]).name == "broken" else CommandResult("ok\n", "", 0)

    monkeypatch.setattr(
        "fmind_dot.cli.State", lambda **_kw: State(runner=ScriptedRunner({"git", "broken"}, run=doc_run))
    )
    monkeypatch.setattr(shutil, "disk_usage", lambda _p: SimpleNamespace(free=200 * 1024**3))
    monkeypatch.setattr(system_module, "available_memory_bytes", lambda: 8 * 1024**3)
    res_def = CliRunner().invoke(app, ["doctor"])
    assert res_def.exit_code == 1
    assert "tools (1)" in res_def.stdout
    assert "capability probes passed" in res_def.stdout
    assert "✗ broken" in res_def.stdout

    res_qt = CliRunner().invoke(app, ["doctor", "-q"])
    assert res_qt.exit_code == 1
    assert "FAIL · doctor:" in res_qt.stdout
    assert "[tools] broken" in res_qt.stdout

    res_qj = CliRunner().invoke(app, ["doctor", "-q", "--json"])
    assert res_qj.exit_code == 1
    qdoc = json.loads(res_qj.stdout)
    assert qdoc["passed"] is False
    assert all(c["status"] in {"fail", "warn"} for c in qdoc["checks"])

    monkeypatch.setattr(system_module, "DOCTOR_TOOLS", ("git",))
    monkeypatch.setattr(
        "fmind_dot.cli.State",
        lambda **_kw: State(runner=ScriptedRunner({"git"}, run=lambda *_a: CommandResult("ok\n", "", 0))),
    )
    res_pass_qj = CliRunner().invoke(app, ["doctor", "-q", "--json"])
    assert res_pass_qj.exit_code == 0
    assert len(res_pass_qj.stdout.encode("utf-8")) < 150
    assert json.loads(res_pass_qj.stdout) == {
        "schema": "dot.diagnostics/v1",
        "scope": "workstation",
        "passed": True,
        "checks": [],
    }
    res_hr_qj = CliRunner().invoke(app, ["doctor", "--headroom", "-q", "--json"])
    assert res_hr_qj.exit_code == 0
    assert json.loads(res_hr_qj.stdout)["checks"] == []

    # --headroom -q text mode omits passing details when healthy and hides passing items when failing
    res_hr_q_pass = CliRunner().invoke(app, ["doctor", "--headroom", "-q"])
    assert res_hr_q_pass.exit_code == 0
    assert res_hr_q_pass.stdout.strip().startswith("PASS · headroom:")
    assert "GiB free" not in res_hr_q_pass.stdout
    assert "GiB available" not in res_hr_q_pass.stdout

    monkeypatch.setattr(system_module, "available_memory_bytes", lambda: 0)
    res_hr_q_fail = CliRunner().invoke(app, ["doctor", "--headroom", "-q"])
    assert res_hr_q_fail.exit_code == 1
    assert "FAIL · headroom: memory" in res_hr_q_fail.stdout
    assert "GiB free" not in res_hr_q_fail.stdout


def test_system_and_auth_coverage_branches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    # _inspect_secret edge cases
    sec = tmp_path / "sec"
    sec.write_text("k", encoding="utf-8")
    sec.chmod(0o644)
    assert system_module._inspect_secret(str(sec), fix=False).status == "fail"  # noqa: SLF001
    sec.chmod(0o600)
    assert system_module._inspect_secret(str(sec), fix=False).status == "pass"  # noqa: SLF001
    with monkeypatch.context() as mp:
        mp.setattr(os, "getuid", lambda: 99999)
        assert "not owned" in system_module._inspect_secret(str(sec), fix=False).details  # noqa: SLF001
    with monkeypatch.context() as mp:
        mp.setattr(Path, "lstat", lambda _self: (_ for _ in ()).throw(PermissionError("denied")))
        assert "unable to inspect" in system_module._inspect_secret(str(sec), fix=False).details  # noqa: SLF001
    sec.chmod(0o644)
    with monkeypatch.context() as mp:
        mp.setattr(os, "fchmod", lambda *_a: (_ for _ in ()).throw(PermissionError("ro")))
        assert "repair failed" in system_module._inspect_secret(str(sec), fix=True).details  # noqa: SLF001

    # _probe OSError, _docker_results timeout, _auth_results failure branches
    err_runner = ScriptedRunner(
        {"docker", "gh"},
        run=lambda cmd, *_a: (_ for _ in ()).throw(CommandTimeoutError("t") if cmd[0] == "docker" else OSError("io")),
    )
    st_err = make_state(err_runner)
    assert system_module._probe(st_err, ["gh"]) == "failed"  # noqa: SLF001
    assert system_module._docker_results(st_err)[0].status == "fail"  # noqa: SLF001

    cfg = Config(auth=AuthConfig(login=["github", "gcp", "workspace"]))
    st_auth_fail = make_state(
        ScriptedRunner({"gh", "gcloud"}, run=lambda *_a: CommandResult(json.dumps({"hosts": {}}), "", 0)), cfg
    )
    monkeypatch.setattr(system_module, "github_ready", lambda *_a, **_kw: False)
    monkeypatch.setattr(system_module, "gcloud_ready", lambda *_a, **_kw: (_ for _ in ()).throw(DotError("boom")))
    monkeypatch.setattr(system_module, "adc_ready", lambda *_a, **_kw: True)
    auth_map = {r.name: r.status for r in system_module._auth_results(st_auth_fail)}  # noqa: SLF001
    assert auth_map == {"gh": "fail", "gcloud": "fail", "gcloud-adc": "pass", "gws": "skip"}

    monkeypatch.setattr(system_module, "github_ready", lambda *_a, **_kw: True)
    monkeypatch.setattr(system_module, "github_token_plaintext", lambda _e: False)
    assert next(r for r in system_module._auth_results(st_auth_fail) if r.name == "gh").status == "pass"  # noqa: SLF001

    # _install_results branches
    st_chez_bad = make_state(ScriptedRunner({"chezmoi"}, run=lambda *_a: CommandResult("", "err", 1)))
    assert system_module._install_results(st_chez_bad)[0].status == "warn"  # noqa: SLF001
    non_dot = tmp_path / "non_dot"
    non_dot.mkdir()
    st_nondot = make_state(ScriptedRunner({"chezmoi"}, run=lambda *_a: CommandResult(str(non_dot), "", 0)))
    assert system_module._install_results(st_nondot)[0].status == "skip"  # noqa: SLF001
    src_dot = tmp_path / "src_dot"
    (src_dot / "dot/src/fmind_dot").mkdir(parents=True)
    (src_dot / "dot/pyproject.toml").write_text("[bad toml", encoding="utf-8")
    st_srcdot = make_state(ScriptedRunner({"chezmoi"}, run=lambda *_a: CommandResult(str(src_dot), "", 0)))
    with monkeypatch.context() as mp:
        mp.setattr(system_module, "PACKAGE_DIRECTORY", src_dot / "dot/src/fmind_dot")
        assert "source checkout" in system_module._install_results(st_srcdot)[0].details  # noqa: SLF001
    with monkeypatch.context() as mp:
        mp.setattr(system_module, "PACKAGE_DIRECTORY", tmp_path / "site/fmind_dot")
        assert system_module._install_results(st_srcdot)[0].status == "fail"  # noqa: SLF001

    # _inspect_agent healthy check
    (tmp_path / ".agents/skills/s").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".agents/AGENTS.md").write_text("# P\n")
    (tmp_path / ".agents/skills/s/SKILL.md").write_text("---\nname: s\ndescription: s\nlicense: MIT\n---\n")
    pp = system_module.expand_path(system_module._AGENT_HOSTS["copilot"][0])  # noqa: SLF001
    pp.parent.mkdir(parents=True, exist_ok=True)
    if not pp.exists():
        pp.symlink_to(tmp_path / ".agents/AGENTS.md")
    cr = system_module.expand_path(system_module._AGENT_REVIEWERS["copilot"][0])  # noqa: SLF001
    cr.mkdir(parents=True, exist_ok=True)
    (cr / "fmind-review-code.agent.md").write_text("---\nname: fmind-review-code\n---\n")
    assert system_module._inspect_agent("copilot").status == "pass"  # noqa: SLF001

    # available_memory_bytes & headroom_results edge cases
    with monkeypatch.context() as mp:
        mp.setattr(sys, "platform", "darwin")
        assert available_memory_bytes() is None
    bad_mem = tmp_path / "bad_mem"
    bad_mem.write_text("MemAvailable: bad\n", encoding="utf-8")
    assert available_memory_bytes(bad_mem) is None
    with monkeypatch.context() as mp:
        mp.setattr(system_module, "available_memory_bytes", lambda: None)
        mp.setattr(shutil, "disk_usage", lambda _p: (_ for _ in ()).throw(OSError("no disk")))
        hr = headroom_results([tmp_path])
        assert {r.name: r.status for r in hr} == {"disk": "warn", "memory": "warn"}
    with monkeypatch.context() as mp:
        mp.setattr(Path, "resolve", lambda _self: (_ for _ in ()).throw(OSError("loop")))
        hr_res = headroom_results([tmp_path], memory=8 * 1024**3)
        assert hr_res[0].status == "warn"

    # auth.py branches
    monkeypatch.setenv("GOOGLE_WORKSPACE_CLI_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_WORKSPACE_CLI_CLIENT_SECRET", "csec")
    assert auth_module._has_env_workspace_client() is True  # noqa: SLF001
    st_ws_bad = make_state(ScriptedRunner({"gws"}, run=lambda *_a: CommandResult("[]", "", 0)))
    with pytest.raises(DotError, match="client configuration state is unknown"):
        auth_module._workspace_client(st_ws_bad, "p1")  # noqa: SLF001
    st_ws_dry = make_state()
    auth_module.login_workspace(st_ws_dry, dry_run=True, project="my-proj-1")
    assert "gws auth setup" in buf(st_ws_dry.stdout)

    st_en = make_state(ScriptedRunner({"gcloud"}, run=lambda *_a: CommandResult("", "boom\n", 1)))
    with pytest.raises(DotError, match="command failed"):
        auth_module._enable_workspace_apis(st_en, ["drive.googleapis.com"], "my-proj-1", allow_permission_denied=False)  # noqa: SLF001
    assert "boom" in buf(st_en.stderr)

    monkeypatch.setattr(auth_module, "WORKSPACE_SCOPE_LIMIT", 1)
    with pytest.raises(DotError, match="scope limit"):
        auth_module.login_workspace(make_state(config=cfg))
    monkeypatch.setattr(auth_module, "WORKSPACE_SCOPE_LIMIT", 50)

    monkeypatch.delenv("GWS_PROJECT", raising=False)
    monkeypatch.delenv("GOOGLE_WORKSPACE_CLI_CLIENT_ID")
    st_no_proj = make_state(
        ScriptedRunner({"gws"}, run=lambda *_a: CommandResult(json.dumps({"token_valid": False}), "", 0))
    )
    with pytest.raises(DotError, match="did not satisfy"):
        auth_module.login_workspace(st_no_proj)
    assert "Skipping Workspace setup" in buf(st_no_proj.stderr)

    st_setup_ready = make_state(
        ScriptedRunner(
            {"gcloud", "gws"},
            responses={
                ("gws", "auth", "status"): [
                    CommandResult(json.dumps({"client_config_exists": False, "enabled_apis": []}), "", 0),
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
                    ),
                ]
            },
        ),
        cfg,
    )
    auth_module.login_workspace(st_setup_ready, setup=True, project="my-proj-1")
    assert "already authenticated" in buf(st_setup_ready.stderr)

    st_incomplete = make_state(
        ScriptedRunner(
            {"gcloud", "gws"},
            run=lambda *_a: CommandResult(json.dumps({"client_config_exists": False, "enabled_apis": []}), "", 0),
        )
    )
    with pytest.raises(DotError, match="setup is incomplete"):
        auth_module.setup_workspace(st_incomplete, "my-proj-1")

    # login_github, login_gcp, provider_ready, check_logins, login_machine, CLI login --dry-run
    gh_ok = {"active": True, "state": "success", "scopes": ", ".join(auth_module.GITHUB_SCOPES)}
    st_gh_ready = make_state(
        ScriptedRunner({"gh"}, run=lambda *_a: CommandResult(json.dumps({"hosts": {"github.com": [gh_ok]}}), "", 0))
    )
    auth_module.login_github(st_gh_ready)
    assert "already authenticated" in buf(st_gh_ready.stderr)

    st_gh_fail = make_state(
        ScriptedRunner({"gh"}, run=lambda *_a: CommandResult(json.dumps({"hosts": {"github.com": []}}), "", 0))
    )
    monkeypatch.setattr(st_gh_fail.runner, "interactive", lambda *_a, **_k: 0)
    with pytest.raises(DotError, match="did not satisfy"):
        auth_module.login_github(st_gh_fail)

    gh_grant_entry = {
        "active": True,
        "state": "success",
        "scopes": ", ".join([*auth_module.GITHUB_SCOPES, "write:ssh_signing_key"]),
    }
    gh_grant_runner = ScriptedRunner(
        {"gh"}, run=lambda *_a: CommandResult(json.dumps({"hosts": {"github.com": [gh_grant_entry]}}), "", 0)
    )
    monkeypatch.setattr(gh_grant_runner, "interactive", lambda *_a, **_k: 0)
    st_gh_grant = make_state(gh_grant_runner)
    auth_module.login_github(st_gh_grant, force=True, grants=["write:ssh_signing_key"])
    assert "One-off GitHub scopes granted" in buf(st_gh_grant.stderr)

    st_gcp_ok = make_state(ScriptedRunner({"gcloud"}, run=lambda *_a: CommandResult("tok\n", "", 0)))
    auth_module.login_gcp(st_gcp_ok)
    assert "already provide usable" in buf(st_gcp_ok.stderr)

    # GCE metadata service account must not satisfy user gcloud/ADC readiness, while non-GCE SA logins still pass.
    sa_responses = {
        tuple(auth_module.GCLOUD_CLI_TOKEN): [CommandResult("sa-tok\n", "", 0)],
        tuple(auth_probes_module.GCLOUD_ACTIVE_ACCOUNT): [CommandResult("vm@example.iam.gserviceaccount.com\n", "", 0)],
    }
    monkeypatch.setattr(auth_probes_module, "is_gce_vm", lambda: False)
    assert (
        auth_module.gcloud_ready(
            make_state(ScriptedRunner({"gcloud"}, responses=sa_responses)), auth_module.GCLOUD_CLI_TOKEN
        )
        is True
    )
    monkeypatch.setattr(auth_probes_module, "is_gce_vm", lambda: True)
    assert (
        auth_module.gcloud_ready(
            make_state(ScriptedRunner({"gcloud"}, responses=sa_responses)), auth_module.GCLOUD_CLI_TOKEN
        )
        is False
    )
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    assert (
        auth_module.adc_ready(make_state(ScriptedRunner({"gcloud"}, run=lambda *_a: CommandResult("t\n", "", 0))))
        is False
    )
    monkeypatch.setattr(auth_probes_module, "is_gce_vm", lambda: False)

    # Headless SSH and display-less Linux (e.g., Remote Control daemon) pass --no-launch-browser.
    monkeypatch.setenv("SSH_TTY", "/dev/pts/0")
    st_ssh_dry = make_state()
    auth_module.login_gcp(st_ssh_dry, dry_run=True)
    assert buf(st_ssh_dry.stdout).count("--no-launch-browser") == 2
    monkeypatch.delenv("SSH_TTY", raising=False)
    monkeypatch.delenv("SSH_CONNECTION", raising=False)
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    with monkeypatch.context() as mp:
        mp.setattr(sys, "platform", "linux")
        assert auth_probes_module.is_headless_ssh() is True
        mp.setenv("DISPLAY", ":0")
        assert auth_probes_module.is_headless_ssh() is False

    # Headless GCE accepts 0600 gh hosts.yml without false keyring warnings, but still flags 0644.
    hosts_file = tmp_path / "hosts.yml"
    hosts_file.write_text("github.com:\n", encoding="utf-8")
    hosts_file.chmod(0o600)
    with monkeypatch.context() as mp:
        mp.setattr(auth_probes_module, "is_gce_vm", lambda: True)
        mp.setattr(auth_probes_module, "is_headless_ssh", lambda: True)
        assert auth_probes_module.github_plaintext_headless_ok({"tokenSource": str(hosts_file)}) is True
        hosts_file.chmod(0o644)
        assert auth_probes_module.github_plaintext_headless_ok({"tokenSource": str(hosts_file)}) is False

    adc_probe_key = tuple(auth_module._adc_cmd("print-access-token"))  # noqa: SLF001
    gcp_adc_runner = ScriptedRunner(
        {"gcloud"},
        responses={
            ("gcloud", "auth", "print-access-token"): [CommandResult("t\n", "", 0), CommandResult("t\n", "", 0)],
            adc_probe_key: [
                CommandResult("", "Reauthentication", 1),
                CommandResult("t\n", "", 0),
            ],
        },
    )
    auth_module.login_gcp(make_state(gcp_adc_runner))
    assert any("application-default" in c and "login" in c for c in gcp_adc_runner.calls)

    gcp_fail = ScriptedRunner(
        {"gcloud"},
        run=lambda cmd, *_a: (
            CommandResult("", "Reauthentication", 1) if "print-access-token" in cmd else CommandResult("", "", 0)
        ),
    )
    with pytest.raises(DotError, match="did not provide usable CLI and ADC"):
        auth_module.login_gcp(make_state(gcp_fail))

    assert auth_module.provider_ready(st_gh_ready, "github") is True
    st_all_ready = make_state(
        ScriptedRunner({"gh"}, run=lambda *_a: CommandResult(json.dumps({"hosts": {"github.com": [gh_ok]}}), "", 0))
    )
    auth_module.check_logins(st_all_ready, ["github"], "dot login", force=False, dry_run=False)
    assert "github: ready" in buf(st_all_ready.stdout)

    cfg_gh = Config(auth=AuthConfig(login=["github"]))
    st_lm = make_state(
        ScriptedRunner({"gh"}, run=lambda *_a: CommandResult(json.dumps({"hosts": {"github.com": [gh_ok]}}), "", 0)),
        cfg_gh,
    )
    auth_module.login_machine(st_lm, force=False, dry_run=False, check=True)
    auth_module.login_machine(st_lm, force=False, dry_run=True, check=False)
    assert "gh auth login" in buf(st_lm.stdout)

    monkeypatch.setattr("fmind_dot.state.State.config", cfg_gh)
    res_cli_login = CliRunner().invoke(app, ["login", "github", "--dry-run"])
    assert res_cli_login.exit_code == 0
    assert "gh auth login" in res_cli_login.stdout

    # Non-TTY interactive login fails closed immediately instead of hanging (both stdin and stdout must be TTYs)
    from fmind_dot.process import Runner

    non_tty_runner = Runner()
    monkeypatch.setattr(non_tty_runner, "which", lambda _cmd: Path("/bin/gh"))
    non_tty_state = make_state(non_tty_runner)
    with pytest.raises(DotError, match="requires a terminal"):
        auth_probes_module.execute(non_tty_state, ["gh", "auth", "login"])

    for stdin_stream, stdout_stream in (
        (io.StringIO(), TerminalIO()),
        (TerminalIO(), io.StringIO()),
    ):
        half_tty = State(runner=non_tty_runner, stdin=stdin_stream, stdout=stdout_stream, stderr=io.StringIO())
        with pytest.raises(DotError, match="requires a terminal"):
            auth_probes_module.execute(half_tty, ["gh", "auth", "login"])

    tty_calls: list[list[str]] = []
    monkeypatch.setattr(non_tty_runner, "interactive", lambda args, **_k: (tty_calls.append(list(args)), 0)[1])
    full_tty = State(runner=non_tty_runner, stdin=TerminalIO(), stdout=TerminalIO(), stderr=io.StringIO())
    auth_probes_module.execute(full_tty, ["gh", "auth", "login"])
    assert tty_calls == [["gh", "auth", "login"]]

    # Non-TTY setup_workspace / login_workspace fail closed BEFORE mutating GCP via gcloud services enable
    cfg_ws = Config(auth=AuthConfig(login=["workspace"]))
    ws_calls: list[list[str]] = []

    def ws_probe(cmd: list[str], *_a: object, **_kw: object) -> CommandResult:
        ws_calls.append(list(cmd))
        return CommandResult(json.dumps({"client_config_exists": False, "enabled_apis": []}), "", 0)

    monkeypatch.setattr(non_tty_runner, "which", lambda cmd: Path("/bin") / cmd)
    monkeypatch.setattr(non_tty_runner, "run", ws_probe)
    for action in (
        lambda st: auth_module.setup_workspace(st, "my-proj-1"),
        lambda st: auth_module.login_workspace(st, project="my-proj-1"),
    ):
        ws_calls.clear()
        with pytest.raises(DotError, match="requires a terminal"):
            action(make_state(non_tty_runner, cfg_ws))
        assert ws_calls == [["gws", "auth", "status"]]

    # Configured client + --setup + logged out fails closed BEFORE gcloud services enable in non-TTY
    ws_calls.clear()
    ws_logged_out = json.dumps(
        {"client_config_exists": True, "project_id": "my-proj-1", "enabled_apis": [], "token_valid": False}
    )
    monkeypatch.setattr(
        non_tty_runner,
        "run",
        lambda cmd, *_a, **_kw: (ws_calls.append(list(cmd)), CommandResult(ws_logged_out, "", 0))[1],
    )
    with pytest.raises(DotError, match="requires a terminal"):
        auth_module.login_workspace(make_state(non_tty_runner, cfg_ws), project="my-proj-1", setup=True)
    assert ws_calls == [["gws", "auth", "status"]]

    # --dry-run and --check continue to work without a TTY
    dry_non_tty = make_state(non_tty_runner, cfg_ws)
    auth_module.login_workspace(dry_non_tty, project="my-proj-1", dry_run=True)
    assert "gcloud services enable" in buf(dry_non_tty.stdout)
    with pytest.raises(SystemExit) as chk_exit:
        auth_module.check_logins(
            make_state(non_tty_runner, cfg_ws), ["workspace"], "dot login workspace", force=False, dry_run=False
        )
    assert chk_exit.value.code == 1

    # GCE VM probes fail closed when `gcloud auth list` fails, and `adc_ready` honors CLOUDSDK_CONFIG.
    monkeypatch.setattr(auth_probes_module, "is_gce_vm", lambda: True)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.delenv("CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE", raising=False)
    monkeypatch.delenv("CLOUDSDK_AUTH_ACCESS_TOKEN", raising=False)

    def gce_fail_list(cmd: list[str], *_a: object) -> CommandResult:
        if cmd == auth_probes_module.GCLOUD_ACTIVE_ACCOUNT:
            return CommandResult("", "broken", 1)
        return CommandResult("tok\n", "", 0)

    with pytest.raises(DotError, match="authentication state is unknown"):
        auth_probes_module.gcloud_ready(
            make_state(ScriptedRunner({"gcloud"}, run=gce_fail_list)), auth_probes_module.GCLOUD_CLI_TOKEN
        )

    custom_gcloud = tmp_path / "custom-gcloud"
    custom_gcloud.mkdir()
    monkeypatch.setenv("CLOUDSDK_CONFIG", str(custom_gcloud))
    st_adc = make_state(ScriptedRunner({"gcloud"}, run=lambda *_a: CommandResult("tok\n", "", 0)))
    assert auth_probes_module.adc_ready(st_adc) is False
    (custom_gcloud / "application_default_credentials.json").write_text("{}", encoding="utf-8")
    assert (
        auth_probes_module.adc_ready(
            make_state(ScriptedRunner({"gcloud"}, run=lambda *_a: CommandResult("tok\n", "", 0)))
        )
        is True
    )
