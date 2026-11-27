from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from fmind_dot import auth as auth_module
from fmind_dot import auth_probes as auth_probes_module
from fmind_dot.cli import app
from fmind_dot.config import WORKSPACE_APIS, AuthConfig, Config
from fmind_dot.errors import DotError, UsageError
from fmind_dot.process import CommandResult, Runner
from fmind_dot.state import State
from tests.fakes import CliRunner, ScriptedRunner, TerminalIO, buf, make_state


def test_github_and_gcp_login_flows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    st_dry = make_state(ScriptedRunner({"gh"}))
    auth_module.login_github(st_dry, dry_run=True, grants=["write:ssh_signing_key"])
    dry_out = buf(st_dry.stdout)
    assert "--web --clipboard" in dry_out
    assert "gh auth refresh" in dry_out
    assert "--remove-scopes admin:enterprise" in dry_out
    assert "delete_repo" not in dry_out
    with pytest.raises(UsageError, match="forbidden by security policy"):
        auth_module.login_github(make_state(ScriptedRunner({"gh"})), dry_run=True, grants=["admin:enterprise"])

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

    st_gh_ready = make_state(
        ScriptedRunner({"gh"}, run=lambda *_a: CommandResult(json.dumps({"hosts": {"github.com": [entry_ok]}}), "", 0))
    )
    auth_module.login_github(st_gh_ready)
    assert "already authenticated" in buf(st_gh_ready.stderr)

    # Plaintext warning prints on non-headless hosts.yml and stays silent on headless GCE 0600 hosts.yml.
    hosts_file = tmp_path / "hosts.yml"
    hosts_file.write_text("github.com:\n", encoding="utf-8")
    hosts_file.chmod(0o600)
    plaintext_entry = {**entry_ok, "tokenSource": str(hosts_file)}
    with monkeypatch.context() as mp:
        mp.setattr(auth_probes_module, "is_gce_vm", lambda: False)
        st_plain = make_state(
            ScriptedRunner(
                {"gh"}, run=lambda *_a: CommandResult(json.dumps({"hosts": {"github.com": [plaintext_entry]}}), "", 0)
            )
        )
        auth_module.login_github(st_plain)
        assert "plaintext hosts.yml" in buf(st_plain.stderr)

    with monkeypatch.context() as mp:
        mp.setattr(auth_probes_module, "is_gce_vm", lambda: True)
        mp.setattr(auth_probes_module, "is_headless_ssh", lambda: True)
        st_headless = make_state(
            ScriptedRunner(
                {"gh"}, run=lambda *_a: CommandResult(json.dumps({"hosts": {"github.com": [plaintext_entry]}}), "", 0)
            )
        )
        auth_module.login_github(st_headless)
        assert "plaintext hosts.yml" not in buf(st_headless.stderr)

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

    st_gcp_dry = make_state()
    auth_module.login_gcp(st_gcp_dry, dry_run=True)
    assert "application-default login" in buf(st_gcp_dry.stdout)

    with monkeypatch.context() as mp:
        mp.setenv("SSH_TTY", "/dev/pts/0")
        st_ssh_dry = make_state()
        auth_module.login_gcp(st_ssh_dry, dry_run=True)
        assert buf(st_ssh_dry.stdout).count("--no-launch-browser") == 2

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

    st_gcp_ok = make_state(ScriptedRunner({"gcloud"}, run=lambda *_a: CommandResult("tok\n", "", 0)))
    auth_module.login_gcp(st_gcp_ok)
    assert "already provide usable" in buf(st_gcp_ok.stderr)

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


def test_workspace_setup_and_login_flows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("GOOGLE_WORKSPACE_CLI_CONFIG_DIR", raising=False)
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

    for bad_grant in ("cloud-platform", "https://mail.google.com", "HTTPS://MAIL.GOOGLE.COM/"):
        with pytest.raises(UsageError, match="forbidden by security policy"):
            auth_module.login_workspace(make_state(ScriptedRunner({"gws"}), cfg), dry_run=True, grants=[bad_grant])
    with pytest.raises(UsageError, match="--setup requires a project ID"):
        auth_module.login_workspace(make_state(ScriptedRunner({"gws"})), dry_run=True, setup=True)

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

    # Existing valid client for a different or unknown project fails closed unless --setup is explicit.
    mismatch_status = json.dumps(
        {
            "client_config_exists": True,
            "project_id": "other-proj",
            "enabled_apis": list(WORKSPACE_APIS),
            "token_valid": True,
            "scopes": list(cfg.auth.workspace.scopes),
        }
    )
    mismatch_runner = ScriptedRunner({"gcloud", "gws"}, run=lambda *_a: CommandResult(mismatch_status, "", 0))
    with pytest.raises(DotError, match="configured for project 'other-proj', not 'my-proj-1'"):
        auth_module.login_workspace(make_state(mismatch_runner, cfg), project="my-proj-1")
    assert mismatch_runner.calls == [["gws", "auth", "status"]]

    mismatch_runner.calls.clear()
    with pytest.raises(
        DotError, match="run dot login workspace --project other-proj or run dot login workspace --setup"
    ):
        auth_module.login_workspace(make_state(mismatch_runner, cfg), force=True, project="my-proj-1")
    assert mismatch_runner.calls == [["gws", "auth", "status"]]

    for unknown_payload in (
        {"client_config_exists": True, "enabled_apis": []},
        {"client_config_exists": True, "project_id": None, "enabled_apis": []},
        {"client_config_exists": True, "project_id": "", "enabled_apis": []},
    ):
        unk_runner = ScriptedRunner(
            {"gcloud", "gws"}, run=lambda *_a, p=unknown_payload: CommandResult(json.dumps(p), "", 0)
        )
        with pytest.raises(DotError, match="unknown project, not 'my-proj-1'; update the project setting"):
            auth_module.login_workspace(make_state(unk_runner, cfg), project="my-proj-1")
        assert unk_runner.calls == [["gws", "auth", "status"]]

    bad_id_runner = ScriptedRunner(
        {"gcloud", "gws"},
        run=lambda *_a: CommandResult(json.dumps({"client_config_exists": True, "project_id": "BAD\nID"}), "", 0),
    )
    with pytest.raises(DotError, match="update the project setting or run dot login workspace --setup") as bad_id_err:
        auth_module.login_workspace(make_state(bad_id_runner, cfg), project="my-proj-1")
    assert "--project" not in str(bad_id_err.value)

    with monkeypatch.context() as mp:
        mp.setenv("GOOGLE_WORKSPACE_CLI_CONFIG_DIR", str(tmp_path / "gws-alt"))
        mismatch_runner.calls.clear()
        with pytest.raises(
            DotError,
            match="GOOGLE_WORKSPACE_CLI_CONFIG_DIR is set\\); unset GOOGLE_WORKSPACE_CLI_CONFIG_DIR, run dot login workspace --project other-proj",
        ):
            auth_module.login_workspace(make_state(mismatch_runner, cfg), project="my-proj-1")
        assert mismatch_runner.calls == [["gws", "auth", "status"]]

        # Matching --project succeeds even under GOOGLE_WORKSPACE_CLI_CONFIG_DIR.
        mismatch_runner.calls.clear()
        st_match_alt = make_state(mismatch_runner, cfg)
        auth_module.login_workspace(st_match_alt, project="other-proj")
        assert mismatch_runner.calls == [["gws", "auth", "status"]]
        assert "already authenticated" in buf(st_match_alt.stderr)

        st_chk_mismatch = make_state(mismatch_runner, cfg)
        with pytest.raises(SystemExit) as mismatch_exit:
            auth_module.check_logins(st_chk_mismatch, ["workspace"], "dot login", force=False, dry_run=False)
        assert mismatch_exit.value.code == 1
        assert "GOOGLE_WORKSPACE_CLI_CONFIG_DIR is set" in buf(st_chk_mismatch.stdout)

    # --check mirrors login_workspace readiness when the client config is missing or corrupt despite a valid token.
    for unready_client in (
        {"client_config_exists": False, "token_valid": True, "scopes": list(cfg.auth.workspace.scopes)},
        {
            "client_config_exists": True,
            "client_config_error": "invalid json",
            "project_id": "my-proj-1",
            "token_valid": True,
            "scopes": list(cfg.auth.workspace.scopes),
        },
    ):
        unready_runner = ScriptedRunner({"gws"}, run=lambda *_a, p=unready_client: CommandResult(json.dumps(p), "", 0))
        st_chk_unready = make_state(unready_runner, cfg)
        with pytest.raises(SystemExit) as unready_exit:
            auth_module.check_logins(st_chk_unready, ["workspace"], "dot login", force=False, dry_run=False)
        assert unready_exit.value.code == 1
        assert "workspace: login needed" in buf(st_chk_unready.stdout)

    reconfig_runner = ScriptedRunner(
        {"gcloud", "gws"},
        responses={
            ("gws", "auth", "status"): [
                CommandResult(mismatch_status, "", 0),
                CommandResult(
                    json.dumps(
                        {
                            "client_config_exists": True,
                            "project_id": "my-proj-1",
                            "enabled_apis": list(WORKSPACE_APIS),
                            "token_valid": True,
                            "scopes": list(cfg.auth.workspace.scopes),
                        }
                    ),
                    "",
                    0,
                ),
            ]
        },
    )
    auth_module.login_workspace(make_state(reconfig_runner, cfg), setup=True, project="my-proj-1")
    reconfig_enables = [c for c in reconfig_runner.calls if c[:3] == ["gcloud", "services", "enable"]]
    assert [api for c in reconfig_enables for api in c[3:-3]] == list(WORKSPACE_APIS)
    assert all(c[-3:] == ["--project", "my-proj-1", "--quiet"] for c in reconfig_enables)
    assert ["gws", "auth", "setup", "--project", "my-proj-1"] in reconfig_runner.calls

    corrupt_runner = ScriptedRunner(
        {"gcloud", "gws"},
        responses={
            ("gws", "auth", "status"): [
                CommandResult(
                    json.dumps(
                        {
                            "client_config_exists": True,
                            "client_config_error": "invalid json",
                            "project_id": "other-proj",
                            "enabled_apis": [],
                        }
                    ),
                    "",
                    0,
                ),
                CommandResult(
                    json.dumps(
                        {
                            "client_config_exists": True,
                            "project_id": "my-proj-1",
                            "enabled_apis": list(WORKSPACE_APIS),
                            "token_valid": True,
                            "scopes": list(cfg.auth.workspace.scopes),
                        }
                    ),
                    "",
                    0,
                ),
            ]
        },
    )
    auth_module.login_workspace(make_state(corrupt_runner, cfg), project="my-proj-1")
    assert ["gws", "auth", "setup", "--project", "my-proj-1"] in corrupt_runner.calls

    # Additional workspace helper edge cases
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


def test_check_logins_machine_and_cli_guards(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("GWS_PROJECT", raising=False)
    cfg = Config(auth=AuthConfig(login=["gcp", "workspace"]))
    cfg.auth.workspace.project = "my-proj-1"
    runner = ScriptedRunner({"gcloud", "gws"})

    with pytest.raises(UsageError, match="invalid scope"):
        auth_module.one_off_scopes(["not valid!"], [])
    for bad_grant in ("", "/", "-bad", "https://www.googleapis.com/auth/"):
        with pytest.raises(UsageError, match="invalid scope"):
            auth_module.login_workspace(make_state(runner, cfg), dry_run=True, grants=[bad_grant])
    with pytest.raises(UsageError, match="PROJECT"):
        auth_module.login_workspace(make_state(runner, cfg), project="BAD", dry_run=True)
    # Explicit empty --project must fail closed instead of falling back to GWS_PROJECT or config.
    with monkeypatch.context() as mp:
        mp.setenv("GWS_PROJECT", "env-proj-1")
        with pytest.raises(UsageError, match="PROJECT"):
            auth_module.login_workspace(make_state(runner, cfg), project="", dry_run=True)

    # Invalid GWS_PROJECT fails fast with UsageError during --check instead of being swallowed as unknown.
    with monkeypatch.context() as mp:
        mp.setenv("GWS_PROJECT", "BAD")
        with pytest.raises(UsageError, match="PROJECT"):
            auth_module.check_logins(make_state(runner, cfg), ["workspace"], "dot login", force=False, dry_run=False)

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

    gh_ok = {"active": True, "state": "success", "scopes": ", ".join(auth_module.GITHUB_SCOPES)}
    st_gh_ready = make_state(
        ScriptedRunner({"gh"}, run=lambda *_a: CommandResult(json.dumps({"hosts": {"github.com": [gh_ok]}}), "", 0))
    )
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

    with monkeypatch.context() as mp:
        mp.setattr("fmind_dot.state.State.config", cfg)
        mp.setattr(
            "fmind_dot.state.State",
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

    monkeypatch.setattr("fmind_dot.state.State.config", cfg_gh)
    res_cli_login = CliRunner().invoke(app, ["login", "github", "--dry-run"])
    assert res_cli_login.exit_code == 0
    assert "gh auth login" in res_cli_login.stdout


def test_non_tty_interactive_login_guards(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("GWS_PROJECT", raising=False)
    non_tty_runner = Runner()
    monkeypatch.setattr(non_tty_runner, "which", lambda _cmd: Path("/bin/gh"))
    non_tty_state = make_state(non_tty_runner)
    with pytest.raises(DotError, match="requires a terminal"):
        auth_module.execute(non_tty_state, ["gh", "auth", "login"])

    for stdin_stream, stdout_stream in (
        (io.StringIO(), TerminalIO()),
        (TerminalIO(), io.StringIO()),
    ):
        half_tty = State(runner=non_tty_runner, stdin=stdin_stream, stdout=stdout_stream, stderr=io.StringIO())
        with pytest.raises(DotError, match="requires a terminal"):
            auth_module.execute(half_tty, ["gh", "auth", "login"])

    tty_calls: list[list[str]] = []
    monkeypatch.setattr(non_tty_runner, "interactive", lambda args, **_k: (tty_calls.append(list(args)), 0)[1])
    full_tty = State(runner=non_tty_runner, stdin=TerminalIO(), stdout=TerminalIO(), stderr=io.StringIO())
    auth_module.execute(full_tty, ["gh", "auth", "login"])
    assert tty_calls == [["gh", "auth", "login"]]

    # Non-TTY setup_workspace / login_workspace fail closed BEFORE mutating GCP via gcloud services enable.
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

    # Configured client + --setup + logged out fails closed BEFORE gcloud services enable in non-TTY.
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

    # Non-TTY headless login fails closed BEFORE printing interactive SSH curl instructions.
    with monkeypatch.context() as mp:
        mp.setenv("SSH_TTY", "/dev/pts/0")
        st_headless_non_tty = make_state(non_tty_runner, cfg_ws)
        with pytest.raises(DotError, match="requires a terminal"):
            auth_module.login_workspace(st_headless_non_tty, project="my-proj-1")
        assert "Headless SSH detected" not in buf(st_headless_non_tty.stderr)

    # --dry-run and --check continue to work without a TTY.
    dry_non_tty = make_state(non_tty_runner, cfg_ws)
    auth_module.login_workspace(dry_non_tty, project="my-proj-1", dry_run=True)
    assert "gcloud services enable" in buf(dry_non_tty.stdout)
    with pytest.raises(SystemExit) as chk_exit:
        auth_module.check_logins(
            make_state(non_tty_runner, cfg_ws), ["workspace"], "dot login workspace", force=False, dry_run=False
        )
    assert chk_exit.value.code == 1
