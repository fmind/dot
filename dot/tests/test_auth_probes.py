from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from fmind_dot import auth_probes as auth_probes_module
from fmind_dot.config import GITHUB_SCOPES, AuthConfig, Config
from fmind_dot.errors import DotError
from fmind_dot.process import CommandResult
from tests.fakes import ScriptedRunner, make_state


def test_is_gce_vm_handles_non_utf8_dmi_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dmi = tmp_path / "product_name"
    dmi.write_bytes(b"\xff\xfeOEM Board\n")
    monkeypatch.setattr(auth_probes_module, "GCE_DMI_PRODUCT_PATH", dmi)
    assert auth_probes_module.is_gce_vm() is False
    dmi.write_bytes(b"\xffGoogle Compute Engine\n")
    assert auth_probes_module.is_gce_vm() is True


def test_probe_json_and_github_entry_and_scopes() -> None:
    st_bad_exit = make_state(ScriptedRunner({"gh"}, run=lambda *_a: CommandResult("", "boom", 1)))
    with pytest.raises(DotError, match="gh status failed"):
        auth_probes_module.probe_json(st_bad_exit, ["gh", "auth", "status"])

    st_bad_json = make_state(ScriptedRunner({"gh"}, run=lambda *_a: CommandResult("{not-json", "", 0)))
    with pytest.raises(DotError, match="returned invalid status JSON"):
        auth_probes_module.probe_json(st_bad_json, ["gh", "auth", "status"])

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

    entry_forb = {
        "active": True,
        "state": "success",
        "scopes": ", ".join([*GITHUB_SCOPES, "admin:enterprise"]),
    }
    assert auth_probes_module.github_ready(entry_forb, reconcile=False) is False

    entry_disc = {
        "active": True,
        "state": "success",
        "scopes": ", ".join(s for s in [*GITHUB_SCOPES, "write:discussion"] if s != "read:discussion"),
    }
    assert auth_probes_module.github_ready(entry_disc, reconcile=True) is True

    for missing_scopes in ({}, {"scopes": ""}, {"scopes": None}):
        with pytest.raises(DotError, match="did not report OAuth scopes"):
            auth_probes_module.github_ready(missing_scopes, reconcile=False)


def test_headless_ssh_and_github_plaintext_detection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SSH_TTY", raising=False)
    monkeypatch.delenv("SSH_CONNECTION", raising=False)
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    with monkeypatch.context() as mp:
        mp.setattr(sys, "platform", "linux")
        assert auth_probes_module.is_headless_ssh() is True
        mp.setenv("DISPLAY", ":0")
        assert auth_probes_module.is_headless_ssh() is False

    hosts_file = tmp_path / "hosts.yml"
    hosts_file.write_text("github.com:\n", encoding="utf-8")
    hosts_file.chmod(0o600)
    hosts_link = tmp_path / "hosts-link.yml"
    hosts_link.symlink_to(hosts_file)

    assert auth_probes_module.github_token_plaintext({"tokenSource": str(hosts_file)}) is True
    assert auth_probes_module.github_token_plaintext({"tokenSource": "keyring"}) is False

    with monkeypatch.context() as mp:
        mp.setattr(auth_probes_module, "is_gce_vm", lambda: True)
        mp.setattr(auth_probes_module, "is_headless_ssh", lambda: True)
        assert auth_probes_module.github_plaintext_headless_ok({"tokenSource": str(hosts_file)}) is True
        assert auth_probes_module.github_plaintext_headless_ok({"tokenSource": str(hosts_link)}) is False
        with monkeypatch.context() as uid_mp:
            uid_mp.setattr(os, "getuid", lambda: 99999)
            assert auth_probes_module.github_plaintext_headless_ok({"tokenSource": str(hosts_file)}) is False
        hosts_file.chmod(0o644)
        assert auth_probes_module.github_plaintext_headless_ok({"tokenSource": str(hosts_file)}) is False


def test_gce_gcloud_and_adc_readiness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.delenv("CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE", raising=False)
    monkeypatch.delenv("CLOUDSDK_AUTH_ACCESS_TOKEN", raising=False)

    sa_responses = {
        tuple(auth_probes_module.GCLOUD_CLI_TOKEN): [CommandResult("sa-tok\n", "", 0)],
        tuple(auth_probes_module.GCLOUD_ACTIVE_ACCOUNT): [CommandResult("vm@example.iam.gserviceaccount.com\n", "", 0)],
    }
    monkeypatch.setattr(auth_probes_module, "is_gce_vm", lambda: False)
    assert (
        auth_probes_module.gcloud_ready(
            make_state(ScriptedRunner({"gcloud"}, responses=sa_responses)), auth_probes_module.GCLOUD_CLI_TOKEN
        )
        is True
    )

    monkeypatch.setattr(auth_probes_module, "is_gce_vm", lambda: True)
    assert (
        auth_probes_module.gcloud_ready(
            make_state(ScriptedRunner({"gcloud"}, responses=sa_responses)), auth_probes_module.GCLOUD_CLI_TOKEN
        )
        is False
    )

    user_responses = {
        tuple(auth_probes_module.GCLOUD_CLI_TOKEN): [CommandResult("user-tok\n", "", 0)],
        tuple(auth_probes_module.GCLOUD_ACTIVE_ACCOUNT): [CommandResult("alex@example.com\n", "", 0)],
    }
    assert (
        auth_probes_module.gcloud_ready(
            make_state(ScriptedRunner({"gcloud"}, responses=user_responses)), auth_probes_module.GCLOUD_CLI_TOKEN
        )
        is True
    )

    assert (
        auth_probes_module.adc_ready(
            make_state(ScriptedRunner({"gcloud"}, run=lambda *_a: CommandResult("t\n", "", 0)))
        )
        is False
    )

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


def test_workspace_readiness_rejects_forbidden_and_malformed_scopes() -> None:
    cfg = Config(auth=AuthConfig(login=["workspace"]))
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
    assert auth_probes_module.workspace_ready(make_state(forb_runner, cfg)) is False

    bad_runner = ScriptedRunner(
        {"gws"},
        run=lambda *_a: CommandResult(json.dumps({"token_valid": True, "scopes": "not-a-list"}), "", 0),
    )
    with pytest.raises(DotError, match="workspace authentication state is unknown"):
        auth_probes_module.workspace_granted(make_state(bad_runner, cfg))
