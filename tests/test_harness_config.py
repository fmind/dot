"""Exercise chezmoi merges against synthetic host-owned MCP and hook settings."""

import json
import os
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import pytest

from repo_helpers import ROOT, chezmoi, native_binary


class HarnessConfigTests(unittest.TestCase):
    temp: tempfile.TemporaryDirectory[str]
    home: Path
    source: Path
    config: Path

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        # Rendering only needs these includes. Scanning the live checkout races
        # with xdist coverage files being combined and removed by other workers.
        self.source = self.home / "source"
        shutil.copytree(ROOT / ".chezmoitemplates", self.source / ".chezmoitemplates")
        self.config = self.home / "chezmoi.toml"
        self.config.write_text("")

    def render(self, template: str, content: str, overrides: dict[str, str] | None = None) -> str:
        environment = dict(os.environ, HOME=str(self.home))
        for name in ("ANTIGRAVITY_CLOUD_PROJECT", "ANTIGRAVITY_CLOUD_LOCATION"):
            environment.pop(name, None)
        environment.update(overrides or {})
        template_path = self.home / "input.tmpl"
        template_path.write_text((ROOT / template).read_text().removeprefix("# chezmoi:modify-template\n"))
        arguments = ("execute-template", "--with-stdin", "--file", str(template_path))
        return chezmoi(self.source, *arguments, config=self.config, stdin=content, env=environment)

    def test_git_identity_preserves_quotes_backslashes_and_comment_characters(self):
        name = 'Ada "Lovelace" # tools \\ engineering'
        email = "ada@example.com"
        self.config.write_text(f"[data]\ngit_name = {json.dumps(name)}\ngit_email = {json.dumps(email)}\n")
        rendered = self.home / "gitconfig"
        rendered.write_text(self.render("dot_gitconfig.tmpl", ""))
        for key, expected in (("user.name", name), ("user.email", email)):
            result = subprocess.run(
                ["git", "config", "--file", str(rendered), "--get", key],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            assert result.stdout.rstrip("\n") == expected

    def test_personal_checkouts_override_a_work_email(self):
        self.config.write_text(
            '[data]\ngit_name = "Ada"\ngit_email = "ada@work.example"\ngit_personal_email = "ada@personal.example"\n'
        )
        (self.home / ".config/git").mkdir(parents=True)
        (self.home / ".config/git/personal.gitconfig").write_text(
            self.render("dot_config/git/personal.gitconfig.tmpl", "")
        )
        gitconfig = self.home / "gitconfig"
        gitconfig.write_text(self.render("dot_gitconfig.tmpl", ""))
        environment = {
            **os.environ,
            "HOME": str(self.home),
            "GIT_CONFIG_GLOBAL": str(gitconfig),
            "GIT_CONFIG_NOSYSTEM": "1",
        }
        for directory, expected in (
            ("fmind/project", "ada@personal.example"),
            ("source", "ada@personal.example"),
            ("work/project", "ada@work.example"),
        ):
            with self.subTest(directory=directory):
                repository = self.home / directory
                repository.mkdir(parents=True, exist_ok=True)
                subprocess.run(["git", "init", "-q", str(repository)], env=environment, timeout=10, check=True)
                result = subprocess.run(
                    ["git", "-C", str(repository), "config", "user.email"],
                    capture_output=True,
                    text=True,
                    env=environment,
                    timeout=10,
                    check=True,
                )
                assert result.stdout.strip() == expected

    def test_personal_email_defaults_before_chezmoi_init_adds_the_prompt(self):
        self.config.write_text('[data]\ngit_email = "ada@work.example"\n')
        rendered = self.render("dot_config/git/personal.gitconfig.tmpl", "")
        assert 'email = "github@fmind.dev"' in rendered
        assert "name =" not in rendered
        self.config.write_text('[data]\ngit_email = "ada@work.example"\ngit_personal_name = "Ada (Personal)"\n')
        named = self.render("dot_config/git/personal.gitconfig.tmpl", "")
        assert 'name = "Ada (Personal)"' in named

    def test_copilot_merge_preserves_preferences_and_enforces_policy(self):
        template = "private_dot_copilot/modify_private_settings.json"
        original = {
            "model": "account-model",
            "effortLevel": "medium",
            "planEffortLevel": "medium",
            "banner": "always",
            "customAgents": {"defaultLocalOnly": False, "extra": "kept"},
            "ide": {"autoConnect": True, "openDiffOnEdit": False},
            "memory": True,
            "notifications": False,
            "askUser": False,
            "autoUpdate": True,
            "includeCoAuthoredBy": True,
            "trusted_folders": [],
            "customOption": False,
        }
        rendered = self.render(template, json.dumps(original))
        data = json.loads(rendered)
        assert data["model"] == original["model"]
        assert data["effortLevel"] == original["effortLevel"]
        assert data["planEffortLevel"] == original["planEffortLevel"]
        assert data["banner"] == original["banner"]
        assert data["trusted_folders"] == []
        assert data["customOption"] is False
        assert data["customAgents"] == {"defaultLocalOnly": True, "extra": "kept"}
        assert data["ide"] == {"autoConnect": False, "openDiffOnEdit": False}
        assert data["memory"] is False
        assert data["notifications"] is True
        assert data["askUser"] is True
        assert data["autoUpdate"] is False
        assert data["includeCoAuthoredBy"] is False
        assert data["editorMode"] == "vim"
        assert self.render(template, rendered) == rendered
        fresh = json.loads(self.render(template, ""))
        assert fresh["model"] == "auto"
        assert fresh["effortLevel"] == "high"
        assert fresh["planEffortLevel"] == "high"
        assert fresh["customAgents"] == {"defaultLocalOnly": True}
        assert fresh["ide"] == {"autoConnect": False}
        assert fresh["memory"] is False
        assert fresh["theme"] == "default"

    def _expected_agy_denies(self) -> list[str]:
        expected = json.loads(self.render(".chezmoitemplates/agy-secret-denies.tmpl", ""))
        assert {
            f"read_file({self.home / '.private.fish'})",
            f"read_file({self.home / '.local/share/atuin'})",
            f"read_file({self.home / '.cache/huggingface/stored_tokens'})",
            f"read_file({self.home / '.claude/projects'})",
            f"read_file({self.home / '.databrickscfg'})",
            f"read_file({self.home / '.databricks'})",
            f"read_file({self.home / '.genie'})",
            f"read_file({self.home / '.config/acli'})",
            f"read_file({self.home / '.config/cf'})",
            f"read_file({self.home / '.gemini/config/mcp_config.json'})",
            f"read_file({self.home / '.copilot/mcp-config.json'})",
            f"read_file({self.home / '.pgpass'})",
            f"read_file({self.home / '.vault-token'})",
        } <= set(expected)
        assert {"read_file(*.env*)", "read_file(*.pem)", "read_file(*.key)"} <= set(expected)
        assert "read_file(*.age)" not in expected
        return expected

    def test_antigravity_merge_preserves_account_and_explicit_empty_trust(self):
        template = "private_dot_gemini/private_antigravity-cli/modify_private_settings.json"
        original = {
            "model": "account-model",
            "gcp": {"project": "host-project", "location": "host-location", "extra": "preserved"},
            "permissions": {"allow": ["command(git)"], "ask": ["read_url(example.com)"], "deny": ["command(rm -rf)"]},
            "trustedWorkspaces": [],
            "pickerGrouping": "none",
            "verbosity": "low",
            "runningLightSpeed": "slow",
            "colorScheme": "dark",
            "showFeedbackSurvey": True,
            "showTips": True,
            "accountOption": False,
        }
        expected_agy_denies = self._expected_agy_denies()
        rendered = self.render(template, json.dumps(original))
        data = json.loads(rendered)
        for key, value in original.items():
            if key not in {"showFeedbackSurvey", "showTips", "permissions"}:
                assert data[key] == value
        assert data["permissions"] == {
            "allow": original["permissions"]["allow"],
            "ask": original["permissions"]["ask"],
            "deny": ["command(rm -rf)", *expected_agy_denies],
        }
        assert data["showFeedbackSurvey"] is False
        assert data["showTips"] is False
        assert data["editorMode"] == "vim"
        assert data["notifications"] is True
        assert data["queuedMessages"] == "send-immediately"
        assert data["verbosity"] == "low"
        assert data["voice"] == {"voiceMode": "dictation"}
        display = str(self.home / ".gemini/antigravity-cli/display.py")
        for field, mode in [("statusLine", "statusline"), ("title", "title")]:
            assert data[field]["enabled"] is True
            assert shlex.split(data[field]["command"]) == ["exec", "python3", "-I", "-S", display, mode]
        assert self.render(template, rendered) == rendered
        existing_without_verbosity = json.loads(self.render(template, json.dumps({"model": "account-model"})))
        assert existing_without_verbosity["verbosity"] == "medium"
        fresh = json.loads(self.render(template, ""))
        assert fresh["pickerGrouping"] == "grouped"
        assert fresh["queuedMessages"] == "send-immediately"
        assert fresh["showFeedbackSurvey"] is False
        assert fresh["showTips"] is False
        assert fresh["verbosity"] == "medium"
        assert fresh["voice"] == {"voiceMode": "dictation"}
        assert fresh["permissions"] == {"deny": expected_agy_denies}
        for key in ("model", "runningLightSpeed", "colorScheme"):
            assert key not in fresh
        assert "trustedWorkspaces" not in fresh  # dot trust owns folder trust.

    def test_remote_settings_preserve_host_identity_grants_and_projects(self):
        template = "private_dot_gemini/private_config/modify_private_config.json"
        expected_agy_denies = self._expected_agy_denies()
        original = {
            "userSettings": {
                "cliRemoteControlHostname": "fixture-host",
                "themeMode": "THEME_MODE_DARK",
                "globalPermissionGrants": {
                    "allow": ["read_file(/fixture)", "read_file(/fixture)"],
                    "ask": ["execute_url(example.com)"],
                    "deny": ["command(rm *)"],
                },
                "autoExecutionPolicy": "CASCADE_COMMANDS_AUTO_EXECUTION_OFF",
            },
            "customState": {"keep": True},
        }
        rendered = self.render(template, json.dumps(original))
        data = json.loads(rendered)
        settings = data["userSettings"]
        assert settings["cliRemoteControlHostname"] == "fixture-host"
        assert settings["themeMode"] == "THEME_MODE_DARK"
        grants = settings["globalPermissionGrants"]
        managed = [
            "read_file(*)",
            "write_file(*)",
            "command(*)",
            "read_url(*)",
            "execute_url(*)",
            "mcp(*)",
        ]
        assert grants["allow"] == ["read_file(/fixture)", *managed]
        assert grants["ask"] == original["userSettings"]["globalPermissionGrants"]["ask"]
        assert grants["deny"] == ["command(rm *)", *expected_agy_denies]
        assert data["customState"] == original["customState"]
        assert settings["autoExecutionPolicy"] == "CASCADE_COMMANDS_AUTO_EXECUTION_EAGER"
        assert settings["permissionPreset"] == "AGENT_PERMISSION_PRESET_TURBO"
        assert settings["artifactReviewMode"] == "ARTIFACT_REVIEW_MODE_TURBO"
        assert self.render(template, rendered) == rendered
        fresh = json.loads(self.render(template, ""))["userSettings"]
        assert "cliRemoteControlHostname" not in fresh
        assert "themeMode" not in fresh
        assert fresh["globalPermissionGrants"] == {"allow": managed, "deny": expected_agy_denies}

    def test_antigravity_cloud_override_is_explicit_and_json_safe(self):
        template = "private_dot_gemini/private_antigravity-cli/modify_private_settings.json"
        original = json.dumps({"gcp": {"project": "host", "location": "region", "extra": True}})
        location_only = self.render(template, original, {"ANTIGRAVITY_CLOUD_LOCATION": "ignored"})
        assert json.loads(location_only)["gcp"] == json.loads(original)["gcp"]
        for overrides, location in [
            ({}, "global"),
            ({"ANTIGRAVITY_CLOUD_LOCATION": "explicit-region"}, "explicit-region"),
        ]:
            with self.subTest(location=location):
                overrides["ANTIGRAVITY_CLOUD_PROJECT"] = 'project-with-"quote'
                data = json.loads(self.render(template, original, overrides))
                assert data["gcp"] == {"project": 'project-with-"quote', "location": location, "extra": True}

    def test_copilot_lsp_merge_keeps_other_servers_and_ty_options(self):
        template = "private_dot_copilot/modify_lsp-config.json"
        original = {"lspServers": {"custom": {"command": "fixture"}, "ty": {"env": {"CUSTOM": "value"}}}}
        rendered = self.render(template, json.dumps(original))
        data = json.loads(rendered)["lspServers"]
        assert data["custom"] == original["lspServers"]["custom"]
        assert data["ty"]["env"] == {"CUSTOM": "value"}
        assert data["ty"]["command"] == "ty"
        assert data["ty"]["args"] == ["server"]
        assert data["ty"]["fileExtensions"][".py"] == "python"
        assert self.render(template, rendered) == rendered

    def test_antigravity_keybindings_merge_adds_zellij_safe_aliases_and_preserves_host_keys(self):
        template = "private_dot_gemini/private_antigravity-cli/modify_private_keybindings.json"
        original = {"voice.start_dictation": ["f8"], "edit.open_editor": ["ctrl+g"]}
        rendered = self.render(template, json.dumps(original))
        data = json.loads(rendered)
        assert data == {
            "voice.start_dictation": ["f8"],
            "edit.open_editor": ["alt+e", "ctrl+g"],
            "prompt.submit_alternate": ["alt+q", "alt+m"],
            "subagent.jump_to_waiting": ["alt+w", "alt+j"],
        }
        assert self.render(template, rendered) == rendered
        fresh = json.loads(self.render(template, ""))
        assert fresh == {
            "edit.open_editor": ["alt+e", "ctrl+g"],
            "prompt.submit_alternate": ["alt+q", "alt+m"],
            "subagent.jump_to_waiting": ["alt+w", "alt+j"],
        }

    def test_json_merge_rejects_malformed_or_non_object_host_state(self):
        templates = (
            "private_dot_copilot/modify_private_settings.json",
            "private_dot_gemini/private_antigravity-cli/modify_private_settings.json",
            "private_dot_gemini/private_antigravity-cli/modify_private_keybindings.json",
            "private_dot_gemini/private_config/modify_private_config.json",
        )
        for template in templates:
            for content in ['{"unfinished":', "[]", "null", '"string"']:
                with (
                    self.subTest(template=template, content=content),
                    pytest.raises(RuntimeError, match=r"chezmoi failed \(exit 1\)"),
                ):
                    self.render(template, content)

    def test_json_merge_rejects_falsy_invalid_types_and_defaults_null(self):
        agy_secret_count = len(self._expected_agy_denies())
        invalid_cases = [
            (
                "private_dot_gemini/private_antigravity-cli/modify_private_settings.json",
                [{"permissions": value} for value in ([], False, 0, "")],
                r"(?s)chezmoi failed \(exit 1\).*permissions must be an object",
            ),
            (
                "private_dot_gemini/private_antigravity-cli/modify_private_settings.json",
                [{"permissions": {"deny": value}} for value in ({}, False, 0, "")],
                r"(?s)chezmoi failed \(exit 1\).*permissions\.deny must be an array",
            ),
            (
                "private_dot_gemini/private_config/modify_private_config.json",
                [{"userSettings": value} for value in ([], False, 0, "")],
                r"(?s)chezmoi failed \(exit 1\).*userSettings must be an object",
            ),
            (
                "private_dot_gemini/private_config/modify_private_config.json",
                [{"userSettings": {"globalPermissionGrants": value}} for value in ([], False, 0, "")],
                r"(?s)chezmoi failed \(exit 1\).*globalPermissionGrants must be an object",
            ),
            (
                "private_dot_gemini/private_config/modify_private_config.json",
                [{"userSettings": {"globalPermissionGrants": {"allow": value}}} for value in ({}, False, 0, "")],
                r"(?s)chezmoi failed \(exit 1\).*globalPermissionGrants\.allow must be an array",
            ),
            (
                "private_dot_gemini/private_config/modify_private_config.json",
                [{"userSettings": {"globalPermissionGrants": {"deny": value}}} for value in ({}, False, 0, "")],
                r"(?s)chezmoi failed \(exit 1\).*globalPermissionGrants\.deny must be an array",
            ),
        ]
        for template, payloads, pattern in invalid_cases:
            for payload in payloads:
                content = json.dumps(payload)
                with (
                    self.subTest(template=template, content=content),
                    pytest.raises(RuntimeError, match=pattern),
                ):
                    self.render(template, content)

        for payload in ({"permissions": None}, {"permissions": {"deny": None}}, {"permissions": {"deny": []}}):
            data = json.loads(
                self.render(
                    "private_dot_gemini/private_antigravity-cli/modify_private_settings.json", json.dumps(payload)
                )
            )
            assert len(data["permissions"]["deny"]) == agy_secret_count

        for payload in (
            {"userSettings": None},
            {"userSettings": {"globalPermissionGrants": None}},
            {"userSettings": {"globalPermissionGrants": {"allow": None, "deny": None}}},
            {"userSettings": {"globalPermissionGrants": {"allow": [], "deny": []}}},
        ):
            data = json.loads(
                self.render("private_dot_gemini/private_config/modify_private_config.json", json.dumps(payload))
            )
            grants = data["userSettings"]["globalPermissionGrants"]
            assert len(grants["allow"]) == 6
            assert len(grants["deny"]) == agy_secret_count

    def test_json_merge_returns_converged_host_bytes_and_keeps_large_integers(self):
        template = "private_dot_gemini/private_antigravity-cli/modify_private_settings.json"
        converged = json.loads(self.render(template, ""))
        converged["hostCounter"] = 9007199254740993
        host = json.dumps(dict(reversed(converged.items())), indent=4)
        assert self.render(template, host) == host
        drifted = json.loads(self.render(template, json.dumps({"hostCounter": 9007199254740993, "editorMode": "x"})))
        assert drifted["hostCounter"] == 9007199254740993
        assert drifted["editorMode"] == "vim"

    def test_native_jsonc_merges_preserve_comments_when_converged_and_keep_host_values(self):
        template = "private_dot_copilot/modify_private_settings.json"
        assert json.loads(self.render(template, ""))["connectors"] is False
        original = '{/* host preference */ "hostCounter":9007199254740993,"hostUrl":"https://example.com/a//b",}'
        rendered = self.render(template, original)
        data = json.loads(rendered)
        assert data["hostCounter"] == 9007199254740993
        assert data["hostUrl"] == "https://example.com/a//b"
        commented = "// host notes\n" + rendered.rstrip()[:-1].rstrip() + ",\n}\n"
        assert self.render(template, commented) == commented
        with pytest.raises(RuntimeError, match=r"chezmoi failed \(exit 1\)"):
            self.render(template, '{"incomplete": /* unfinished')
        # JSONC support belongs to native formats that support it, not every JSON caller.
        with pytest.raises(RuntimeError, match=r"chezmoi failed \(exit 1\)"):
            self.render("private_dot_copilot/modify_lsp-config.json", original)

    def test_trust_hook_passes_source_path_literally_during_apply(self):
        executable = self.home / ".local/bin/dot"
        executable.parent.mkdir(parents=True)
        executable.write_text('#!/bin/sh\nprintf \'%s\\n\' "$@" >>"$CALL_LOG"\n')
        executable.chmod(0o755)
        log = self.home / "calls"
        for name in ("source with spaces", "source 'quoted' $(printf changed)", r"source `printf changed` $UNSET "):
            with self.subTest(name=name):
                source = self.home / name
                source.mkdir()
                shutil.copyfile(ROOT / "run_after_dot-trust.sh.tmpl", source / "run_after_dot-trust.sh.tmpl")
                log.write_text("")
                environment = {"HOME": str(self.home), "PATH": os.defpath, "CALL_LOG": str(log)}
                chezmoi(source, "apply", "--force", config=self.config, env=environment)
                assert log.read_text().splitlines() == ["trust", "all", str(source)]

    def test_zellij_config_uses_attention_mode_with_notifications_and_validates_natively(self):
        config_path = ROOT / "dot_config/zellij/config.kdl"
        content = config_path.read_text(encoding="utf-8")
        assert 'host_notification_protocol "auto"' in content
        assert 'startup_card "attention"' in content
        assert "track_commands true" in content
        assert "needs_you true" in content
        assert "failed true" in content
        assert "done true" in content
        assert 'unbind "Alt o"' in content
        assert 'bind "Alt Shift i" { ToggleSessionCard; }' in content
        zellij = native_binary("zellij")
        if zellij is None:
            pytest.skip("Zellij native validation requires the workstation tool")
        result = subprocess.run(
            [str(zellij), "-c", str(config_path), "setup", "--check"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        assert "[CONFIG FILE]: Well defined." in result.stdout

    def test_docker_merge_preserves_auths_and_contexts_while_managing_plugin_dirs(self):
        template = "private_dot_docker/modify_private_config.json"
        original = {"auths": {"https://index.docker.io/v1/": {}}, "currentContext": "colima"}
        rendered = self.render(template, json.dumps(original))
        data = json.loads(rendered)
        assert data["auths"] == original["auths"]
        assert data["currentContext"] == "colima"
        assert data["cliPluginsExtraDirs"] == [str(self.home / ".local/share/mise/shims")]
        assert self.render(template, rendered) == rendered


@pytest.mark.parametrize("login", [None, "no-age-key"])
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
    targets = {
        "dot_cache/private_huggingface/create_encrypted_private_token.age": ".cache/huggingface/token",
    }
    for relative in targets:
        assert (ROOT / relative).is_file()
        path = source / relative.replace("encrypted_", "").removesuffix(".age")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic-personal\n")
    environment = {**os.environ, "HOME": str(home)}
    chezmoi(source, "apply", "--force", config=config, env=environment)
    if login == "no-age-key":
        assert all(not (home / relative).exists() for relative in targets.values())
        return
    for relative in targets.values():
        path = home / relative
        assert path.read_text() == "synthetic-personal\n"
        assert path.stat().st_mode & 0o777 == 0o600
        path.write_text("synthetic-customer\n")
    chezmoi(source, "apply", "--force", config=config, env=environment)
    for relative in targets.values():
        assert (home / relative).read_text() == "synthetic-customer\n"
