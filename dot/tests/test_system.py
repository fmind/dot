from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from fmind_dot import auth as auth_module
from fmind_dot import system as system_module
from fmind_dot.cli import app
from fmind_dot.config import AuthConfig, Config
from fmind_dot.errors import CommandTimeoutError, DotError
from fmind_dot.process import CommandResult
from fmind_dot.state import State
from fmind_dot.system import available_memory_bytes, headroom_results, run_doctor
from tests.fakes import CliRunner, ScriptedRunner, doctor_sections, make_state


def _setup_healthy_agents(tmp_path: Path) -> Path:
    shared = tmp_path / ".agents/skills"
    (shared / "s").mkdir(parents=True, exist_ok=True)
    (shared / "s/SKILL.md").write_text("---\nname: s\ndescription: s\nlicense: MIT\n---\n", encoding="utf-8")
    (tmp_path / ".agents/AGENTS.md").write_text("# P\n", encoding="utf-8")
    for persona_path, skills_path in system_module._AGENT_HOSTS.values():  # noqa: SLF001
        pp = system_module.expand_path(persona_path)
        pp.parent.mkdir(parents=True, exist_ok=True)
        if not pp.exists() and not pp.is_symlink():
            pp.symlink_to(tmp_path / ".agents/AGENTS.md")
        if skills_path:
            sp = system_module.expand_path(skills_path)
            sp.parent.mkdir(parents=True, exist_ok=True)
            if not sp.exists() and not sp.is_symlink():
                sp.symlink_to(shared)
    for rev_dir, rev_glob in system_module._AGENT_REVIEWERS.values():  # noqa: SLF001
        rd = system_module.expand_path(rev_dir)
        rd.mkdir(parents=True, exist_ok=True)
        (rd / rev_glob.replace("*", "code")).write_text("---\nname: fmind-review-code\n---\n", encoding="utf-8")
    return shared


def test_secrets_tools_docker_and_install_checks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

    # _inspect_secret edge cases
    secret_file = tmp_path / "sec"
    secret_file.write_text("k", encoding="utf-8")
    secret_file.chmod(0o644)
    assert system_module._inspect_secret(str(secret_file), fix=False).status == "fail"  # noqa: SLF001
    secret_file.chmod(0o600)
    assert system_module._inspect_secret(str(secret_file), fix=False).status == "pass"  # noqa: SLF001
    with monkeypatch.context() as mp:
        mp.setattr(os, "getuid", lambda: 99999)
        assert "not owned" in system_module._inspect_secret(str(secret_file), fix=False).details  # noqa: SLF001
    with monkeypatch.context() as mp:
        mp.setattr(Path, "lstat", lambda _self: (_ for _ in ()).throw(PermissionError("denied")))
        assert "unable to inspect" in system_module._inspect_secret(str(secret_file), fix=False).details  # noqa: SLF001
    secret_file.chmod(0o644)
    with monkeypatch.context() as mp:
        mp.setattr(os, "fchmod", lambda *_a: (_ for _ in ()).throw(PermissionError("ro")))
        assert "repair failed" in system_module._inspect_secret(str(secret_file), fix=True).details  # noqa: SLF001
    fchmod_calls: list[int] = []
    with monkeypatch.context() as mp:
        mp.setattr(os, "fstat", lambda _fd: SimpleNamespace(st_mode=0o040755, st_uid=os.getuid()))
        mp.setattr(os, "fchmod", lambda fd, _m: fchmod_calls.append(fd))
        assert "not a regular file" in system_module._inspect_secret(str(secret_file), fix=True).details  # noqa: SLF001
        assert fchmod_calls == []
    with monkeypatch.context() as mp:
        mp.setattr(os, "fstat", lambda _fd: SimpleNamespace(st_mode=0o100644, st_uid=99999))
        mp.setattr(os, "fchmod", lambda fd, _m: fchmod_calls.append(fd))
        assert "not owned" in system_module._inspect_secret(str(secret_file), fix=True).details  # noqa: SLF001
        assert fchmod_calls == []
    if os.geteuid() != 0:
        secret_file.chmod(0o244)
        repaired = system_module._inspect_secret(str(secret_file), fix=True)  # noqa: SLF001
        assert repaired.status == "pass"
        assert secret_file.stat().st_mode & 0o777 == 0o600

    # _probe OSError and _docker_results timeout
    err_runner = ScriptedRunner(
        {"docker", "gh"},
        run=lambda cmd, *_a: (_ for _ in ()).throw(CommandTimeoutError("t") if cmd[0] == "docker" else OSError("io")),
    )
    st_err = make_state(err_runner)
    assert system_module._probe(st_err, ["gh"]) == "failed"  # noqa: SLF001
    assert system_module._docker_results(st_err)[0].status == "fail"  # noqa: SLF001

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


def test_available_memory_bytes_and_headroom_results(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mem = tmp_path / "meminfo"
    mem.write_text("MemTotal: 1000 kB\nMemAvailable: 8388608 kB\n", encoding="utf-8")
    assert available_memory_bytes(mem) == 8388608 * 1024

    bad_mem = tmp_path / "bad_mem"
    bad_mem.write_text("MemAvailable: bad\n", encoding="utf-8")
    assert available_memory_bytes(bad_mem) is None

    vm_stat_out = (
        "Mach Virtual Memory Statistics: (page size of 16384 bytes)\n"
        "Pages free:                                1000.\n"
        "Pages active:                             50000.\n"
        "Pages inactive:                           20000.\n"
        "Pages speculative:                          500.\n"
    )
    with monkeypatch.context() as mp:
        mp.setattr(sys, "platform", "darwin")
        mp.setattr(subprocess, "run", lambda *_a, **_k: subprocess.CompletedProcess(["vm_stat"], 0, vm_stat_out, ""))
        assert available_memory_bytes() == (1000 + 20000 + 500) * 16384
        mp.setattr(subprocess, "run", lambda *_a, **_k: subprocess.CompletedProcess(["vm_stat"], 1, "", "err"))
        assert available_memory_bytes() is None
        mp.setattr(subprocess, "run", lambda *_a, **_k: subprocess.CompletedProcess(["vm_stat"], 0, "unexpected\n", ""))
        assert available_memory_bytes() is None
        mp.setattr(subprocess, "run", lambda *_a, **_k: (_ for _ in ()).throw(OSError("missing")))
        assert available_memory_bytes() is None

    with monkeypatch.context() as mp:
        mp.setattr(sys, "platform", "win32")
        assert available_memory_bytes() is None

    hr = headroom_results([tmp_path, tmp_path / "missing"], memory=512 * 1024**2)
    assert {r.name: r.status for r in hr}["memory"] == "fail"

    with monkeypatch.context() as mp:
        mp.setattr(system_module, "available_memory_bytes", lambda: None)
        mp.setattr(shutil, "disk_usage", lambda _p: (_ for _ in ()).throw(OSError("no disk")))
        hr_warn = headroom_results([tmp_path])
        assert {r.name: r.status for r in hr_warn} == {"disk": "warn", "memory": "warn"}

    with monkeypatch.context() as mp:
        mp.setattr(Path, "resolve", lambda _self: (_ for _ in ()).throw(OSError("loop")))
        hr_res = headroom_results([tmp_path], memory=8 * 1024**3)
        assert hr_res[0].status == "warn"


def test_doctor_agents_and_agy_isolation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(system_module, "DOCTOR_TOOLS", ("git",))
    monkeypatch.setattr(system_module, "DOCTOR_SECRETS", ())
    _setup_healthy_agents(tmp_path)

    st = make_state(ScriptedRunner({"git"}, run=lambda *_a: CommandResult("ok\n", "", 0)))
    sec = doctor_sections(run_doctor(st, fix=False))
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

    # Multi-tenant agy isolation: global skills.json/plugins.json external paths, fail-closed parsing, and hooks.json hardening.
    skills_json = tmp_path / ".gemini/config/skills.json"
    for payload in (
        {"directories": [{"path": "~/client-secret/skills"}]},
        {"directories": [{"dir": "~/client-secret/skills"}]},
        {"inherits": ["~/client-secret/skills.json"]},
        ["~/client-secret/skills"],
    ):
        skills_json.write_text(json.dumps(payload), encoding="utf-8")
        skills_json.chmod(0o600)
        leaked = {a["name"]: a for a in doctor_sections(run_doctor(st, fix=False))["agents"]}
        assert leaked["agy"]["status"] == "warn"
        assert leaked["agy"]["condition"] == "insecure"
        assert "1 external path(s)" in leaked["agy"]["details"]
        assert "client-secret" not in leaked["agy"]["details"]

    skills_json.write_text(json.dumps({"skills": ["~/client-secret/skills"]}), encoding="utf-8")
    skills_json.chmod(0o600)
    unknown_key = {a["name"]: a for a in doctor_sections(run_doctor(st, fix=False))["agents"]}
    assert unknown_key["agy"]["status"] == "warn"
    assert "unrecognized global entries" in unknown_key["agy"]["details"]
    assert "client-secret" not in unknown_key["agy"]["details"]

    skills_json.write_text(
        json.dumps({"entries": [{"path": "~/.agents/skills", "exclude": ["unused"]}]}), encoding="utf-8"
    )
    skills_json.chmod(0o600)
    assert system_module._inspect_agent("agy").status == "pass"  # noqa: SLF001

    skills_json.write_bytes(b"\xff\xfeinvalid-utf8")
    skills_json.chmod(0o600)
    bad_utf8 = system_module._inspect_agent("agy")  # noqa: SLF001
    assert bad_utf8.status == "warn"
    assert "unreadable or invalid JSON" in bad_utf8.details

    symlink_target = tmp_path / "external_skills.json"
    symlink_target.write_text("{}", encoding="utf-8")
    symlink_target.chmod(0o644)
    skills_json.unlink()
    skills_json.symlink_to(symlink_target)
    sym_warn = system_module._inspect_agent("agy")  # noqa: SLF001
    assert sym_warn.status == "warn"
    assert "unreadable or symlink" in sym_warn.details
    skills_json.unlink()

    plugins_json = tmp_path / ".gemini/config/plugins.json"
    plugins_json.write_text(json.dumps({"entries": [{"path": "~/client-secret/plugins"}]}), encoding="utf-8")
    plugins_json.chmod(0o600)
    plugin_leak = system_module._inspect_agent("agy")  # noqa: SLF001
    assert plugin_leak.status == "warn"
    assert "plugins.json registers 1 external path(s)" in plugin_leak.details
    assert "client-secret" not in plugin_leak.details
    plugins_json.unlink()

    for manifest_name, kind in (("agents.json", "agents"), ("rules.json", "rules")):
        manifest = tmp_path / ".gemini/config" / manifest_name
        manifest.write_text(json.dumps({"entries": [{"path": f"~/client-secret/{kind}"}]}), encoding="utf-8")
        manifest.chmod(0o600)
        leak = system_module._inspect_agent("agy")  # noqa: SLF001
        assert leak.status == "warn"
        assert leak.condition == "insecure"
        assert f"{manifest_name} registers 1 external path(s)" in leak.details
        assert "client-secret" not in leak.details
        manifest.unlink()

    safe_dir = tmp_path / ".local/share/demo"
    safe_dir.mkdir(parents=True, exist_ok=True)
    for ancestor in (tmp_path, tmp_path / ".local", tmp_path / ".local/share", safe_dir):
        ancestor.chmod(0o755)
    hook_script = safe_dir / "hook.py"
    hook_script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    hook_script.chmod(0o755)
    fake_py = safe_dir / "python3"
    fake_py.write_text("#!/bin/sh\n", encoding="utf-8")
    fake_py.chmod(0o777)
    hooks_json = tmp_path / ".gemini/config/hooks.json"
    hooks_json.write_text(
        json.dumps(
            {
                "demo": {
                    "SessionStart": [
                        {"command": f"python3 {hook_script}"},
                        {"command": f"uv run --no-config --locked --script {hook_script} --arg"},
                        {"command": f"uv run --no-config --no-project python3 {hook_script}"},
                        {"command": f"uv run --no-config --no-project --with requests python3 {hook_script}"},
                        {"command": f"uv run --project {safe_dir} python3 {hook_script}"},
                        {"command": f"env -u FOO python3 -W ignore {hook_script}"},
                        {"command": f"SAFE_FLAG=1 python3 {hook_script}"},
                        {"command": "python3 -I -m demo.hook"},
                        {"command": ["python3", str(hook_script)]},
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    hooks_json.chmod(0o600)
    assert system_module._inspect_agent("agy").status == "pass"  # noqa: SLF001

    hook_script.chmod(0o777)
    hooks_json.chmod(0o644)
    bad_hook = system_module._inspect_agent("agy")  # noqa: SLF001
    assert bad_hook.status == "warn"
    assert "permissions too open" in bad_hook.details
    assert "8 invalid, relative, missing, or writable" in bad_hook.details
    hook_script.chmod(0o755)

    writable_dir = tmp_path / ".local/share/writable-proj"
    writable_dir.mkdir(parents=True, exist_ok=True)
    writable_dir.chmod(0o777)
    hooks_json.write_text(
        json.dumps({"demo": {"SessionStart": [{"command": f"uv run --project {writable_dir} python3 {hook_script}"}]}}),
        encoding="utf-8",
    )
    hooks_json.chmod(0o600)
    writable_proj_warn = system_module._inspect_agent("agy")  # noqa: SLF001
    assert writable_proj_warn.status == "warn"
    assert "1 invalid, relative, missing, or writable" in writable_proj_warn.details

    # Script inside a writable parent directory and traversal ending in ".." or "/" fail closed.
    script_in_writable = writable_dir / "owned.py"
    script_in_writable.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    script_in_writable.chmod(0o755)
    uid = os.getuid()
    assert system_module._path_owned_and_unwritable(str(script_in_writable), uid, expect_dir=False) is False  # noqa: SLF001
    assert system_module._path_owned_and_unwritable(f"{safe_dir}/..", uid, expect_dir=False) is False  # noqa: SLF001
    assert system_module._path_owned_and_unwritable("/", uid, expect_dir=False) is False  # noqa: SLF001
    assert system_module._path_owned_and_unwritable(f"{writable_dir}/sub/..", uid, expect_dir=True) is False  # noqa: SLF001
    assert system_module._path_owned_and_unwritable(f"{safe_dir}/..", uid, expect_dir=True) is True  # noqa: SLF001

    # Symlink hop owned by another UID fails closed even when target file is owned and 0755.
    hook_link = safe_dir / "hook-link.py"
    hook_link.symlink_to(hook_script)
    real_lstat = Path.lstat
    with monkeypatch.context() as mp:
        mp.setattr(
            Path,
            "lstat",
            lambda p: SimpleNamespace(st_uid=99999, st_mode=0o120777) if p == hook_link else real_lstat(p),
        )
        assert system_module._path_owned_and_unwritable(str(hook_link), uid, expect_dir=False) is False  # noqa: SLF001

    bypass_cmds: list[object] = [
        "./relative-hook.sh",
        "~otheruser/hook.py",
        "unclosed 'quote",
        "python3 hook.py",
        "python3 -m demo.hook",
        "uv run --no-config --script hook.py",
        "uv run --no-config -s hook.py",
        f"uv run --locked --script {hook_script}",
        f"uv run --no-project python3 {hook_script}",
        f"uv run --no-config --script --with-editable ./evil {hook_script}",
        "uv run --no-config --no-project --gui-script evil",
        f"uv run --no-config --no-project --active python3 {hook_script}",
        f"VIRTUAL_ENV=.venv uv run --no-config --no-project python3 {hook_script}",
        "uv run hook.py",
        f"uv run python3 {hook_script}",
        f"uv run --project {safe_dir} hook.py",
        f"uv run --with-editable {safe_dir} python3 {hook_script}",
        f"uv run --no-config --no-project --python ./evil.sh python3 {hook_script}",
        f"uv run --no-config --no-project -p {fake_py} python3 {hook_script}",
        f"uv run --no-config --no-project --with evil-0.1-py3-none-any.whl python3 {hook_script}",
        f"uv run --no-config --no-project --with evil.tar.gz[dev] python3 {hook_script}",
        f"uv run --no-config --no-project --with evil.tar.bz2 python3 {hook_script}",
        f"uv run --no-project --with requests python3 {hook_script}",
        "uv tool run --from ./evil evil",
        f"uv run --no-config --locked --script={tmp_path / 'missing.py'}",
        f"uv run --project ./rel python3 {hook_script}",
        f"uv run -C./rel python3 {hook_script}",
        "uv -q run ./relative-hook.sh",
        f"uv --directory ./rel run python3 {hook_script}",
        "env -iS 'python3 -c import os'",
        "env -- PYTHONPATH=. sh -c id",
        f"env -C./evil={safe_dir} python3 {hook_script}",
        f"env HOME=. zsh {hook_script}",
        f"env XDG_CONFIG_HOME=. fish {hook_script}",
        f"env BASH_ENV=./evil.sh bash {hook_script}",
        f"env -iu FOO bash {hook_script}",
        f"env ./python3 {hook_script}",
        f"env {fake_py} {hook_script}",
        "X=1 ./relative-hook.sh",
        "BASH_ENV=evil.sh bash /bin/true",
        "python3 $HOME/hook.py",
        "bash -c 'echo bad'",
        "bash +e -c id",
        "bash -O extglob -c id",
        f"fish -C 'echo bad' {hook_script}",
        "sh -m ./relative-hook.sh",
        "python3 -uc 'import os' safe",
        "node -e'process.exit(1)' safe",
        "node -pe '1+1'",
        "node --input-type module -e 1",
        f"eval {hook_script}",
        f"uvx {hook_script}",
        f"(python3 {fake_py})",
        f"python3 {hook_script} arg;id",
        f"foo#bar ; {fake_py}",
        f"true && {hook_script}",
        f"python3 {hook_script} $(id)",
        "",
        "''",
        123,
    ]
    hooks_json.write_text(
        json.dumps({"demo": {"SessionStart": [{"command": c} for c in bypass_cmds]}}),
        encoding="utf-8",
    )
    hooks_json.chmod(0o600)
    rel_hook = system_module._inspect_agent("agy")  # noqa: SLF001
    assert rel_hook.status == "warn"
    assert f"{len(bypass_cmds)} invalid, relative, missing, or writable" in rel_hook.details
    hooks_json.unlink()


def test_doctor_deep_auth_and_workspace_project_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("GWS_PROJECT", raising=False)
    monkeypatch.setattr(system_module, "DOCTOR_TOOLS", ("git",))
    monkeypatch.setattr(system_module, "DOCTOR_SECRETS", ())
    _setup_healthy_agents(tmp_path)

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
    assert {r["name"]: r["status"] for r in sec["auth"]} == {
        "gh": "warn",
        "gcloud": "pass",
        "gcloud-adc": "fail",
        "gws": "skip",
    }

    # doctor --deep catches Workspace OAuth client project mismatch and invalid GWS_PROJECT via provider_ready.
    cfg_ws = Config(auth=AuthConfig(login=["workspace"]))
    cfg_ws.auth.workspace.project = "my-proj-1"
    mismatch_status = json.dumps(
        {
            "client_config_exists": True,
            "project_id": "other-proj",
            "token_valid": True,
            "scopes": list(cfg_ws.auth.workspace.scopes),
        }
    )
    st_ws_mismatch = make_state(
        ScriptedRunner({"gws"}, run=lambda *_a: CommandResult(mismatch_status, "", 0)),
        cfg_ws,
    )
    gws_res = next(r for r in system_module._auth_results(st_ws_mismatch) if r.name == "gws")  # noqa: SLF001
    assert gws_res.status == "fail"
    assert "other-proj" in gws_res.details

    with monkeypatch.context() as mp:
        mp.setenv("GWS_PROJECT", "BAD")
        gws_bad_proj = next(r for r in system_module._auth_results(st_ws_mismatch) if r.name == "gws")  # noqa: SLF001
        assert gws_bad_proj.status == "fail"
        assert "PROJECT" in gws_bad_proj.details

    cfg_all = Config(auth=AuthConfig(login=["github", "gcp", "workspace"]))
    st_auth_fail = make_state(
        ScriptedRunner({"gh", "gcloud"}, run=lambda *_a: CommandResult(json.dumps({"hosts": {}}), "", 0)), cfg_all
    )
    monkeypatch.setattr(system_module, "github_ready", lambda *_a, **_kw: False)
    monkeypatch.setattr(system_module, "gcloud_ready", lambda *_a, **_kw: (_ for _ in ()).throw(DotError("boom")))
    monkeypatch.setattr(system_module, "adc_ready", lambda *_a, **_kw: True)
    auth_map = {r.name: r.status for r in system_module._auth_results(st_auth_fail)}  # noqa: SLF001
    assert auth_map == {"gh": "fail", "gcloud": "fail", "gcloud-adc": "pass", "gws": "skip"}

    monkeypatch.setattr(system_module, "github_ready", lambda *_a, **_kw: True)
    monkeypatch.setattr(system_module, "github_token_plaintext", lambda _e: False)
    assert next(r for r in system_module._auth_results(st_auth_fail) if r.name == "gh").status == "pass"  # noqa: SLF001

    monkeypatch.setattr(system_module, "github_token_plaintext", lambda _e: True)
    monkeypatch.setattr(system_module, "github_plaintext_headless_ok", lambda _e: True)
    gh_headless = next(r for r in system_module._auth_results(st_auth_fail) if r.name == "gh")  # noqa: SLF001
    assert gh_headless.status == "pass"
    assert "headless" in gh_headless.details


def test_doctor_quiet_and_headroom_modes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(system_module, "DOCTOR_TOOLS", ("git", "broken"))
    monkeypatch.setattr(system_module, "DOCTOR_SECRETS", ())
    _setup_healthy_agents(tmp_path)

    assert system_module._inspect_agent("agy").status == "pass"  # noqa: SLF001
    assert system_module._inspect_agent("copilot").status == "pass"  # noqa: SLF001

    def doc_run(cmd: list[str], *_a: object) -> CommandResult:
        return CommandResult("", "err", 1) if Path(cmd[0]).name == "broken" else CommandResult("ok\n", "", 0)

    monkeypatch.setattr(
        "fmind_dot.state.State", lambda **_kw: State(runner=ScriptedRunner({"git", "broken"}, run=doc_run))
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

    res_pass = CliRunner().invoke(app, ["doctor", "--headroom", "--json"])
    assert res_pass.exit_code == 0
    assert json.loads(res_pass.stdout)["scope"] == "headroom"
    txt_pass = CliRunner().invoke(app, ["doctor", "--headroom"])
    assert txt_pass.exit_code == 0
    assert "PASS · headroom:" in txt_pass.stdout

    monkeypatch.setattr(system_module, "DOCTOR_TOOLS", ("git",))
    monkeypatch.setattr(
        "fmind_dot.state.State",
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

    monkeypatch.setattr(shutil, "disk_usage", lambda _p: SimpleNamespace(free=1 * 1024**3))
    res_fail = CliRunner().invoke(app, ["doctor", "--headroom"])
    assert res_fail.exit_code == 1
    assert "FAIL · headroom:" in res_fail.stdout
    bad = CliRunner().invoke(app, ["doctor", "--headroom", "--fix"])
    assert bad.exit_code == 2
