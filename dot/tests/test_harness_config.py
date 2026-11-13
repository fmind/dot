"""Exercise chezmoi merges against synthetic host-owned MCP and hook settings."""

import json
import os
import shlex
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

import pytest

from tests.chezmoi_helpers import chezmoi
from tests.fakes import ROOT, native_binary


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
        # apply consumes the modify-template directive before rendering; execute-template
        # is lower level, so remove that directive to exercise the same template bytes.
        template_path = self.home / "input.tmpl"
        template_path.write_text((ROOT / template).read_text().removeprefix("# chezmoi:modify-template\n"))
        arguments = ("execute-template", "--with-stdin", "--file", str(template_path))
        return chezmoi(self.source, *arguments, config=self.config, stdin=content, env=environment)

    def test_toml_merge_preserves_unmanaged_settings_and_is_repeatable(self):
        original = 'custom = "preserved"\n\n[server.custom]\ncommand = "/synthetic/tool"\n'
        template = "dot_config/marimo/modify_private_marimo.toml"
        rendered = self.render(template, original)
        data = tomllib.loads(rendered)
        assert data["custom"] == "preserved"
        assert data["server"]["custom"]["command"] == "/synthetic/tool"
        assert self.render(template, rendered) == rendered

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

    def test_claude_preserves_host_session_start_hooks_while_retiring_notifications(self):
        template = "private_dot_claude/modify_private_settings.json"
        fresh = json.loads(self.render(template, ""))
        assert "hooks" not in fresh
        assert fresh["agentPushNotifEnabled"] is True
        assert fresh["inputNeededNotifEnabled"] is True
        host_session = [{"hooks": [{"type": "command", "command": "/synthetic/host", "timeout": 30}]}]
        stale_notify = [{"hooks": [{"type": "command", "command": "old"}]}]
        only_notify = json.loads(self.render(template, json.dumps({"hooks": {"Notification": stale_notify}})))
        assert "hooks" not in only_notify
        rendered = self.render(
            template,
            json.dumps({"hooks": {"SessionStart": host_session, "Notification": stale_notify}}),
        )
        hooks = json.loads(rendered)["hooks"]
        assert hooks == {"SessionStart": host_session}
        assert self.render(template, rendered) == rendered

    def test_agy_retires_legacy_notify_hook_while_preserving_host_hooks(self):
        template = "private_dot_gemini/private_config/modify_private_hooks.json"
        assert json.loads(self.render(template, "")) == {}
        host = {
            "brain-context": {"SessionStart": [{"type": "command", "command": "/synthetic/brain", "timeout": 30}]},
            "notify": {"Stop": [], "PreToolUse": []},
            "custom": {"Stop": []},
        }
        rendered = self.render(template, json.dumps(host))
        upgraded = json.loads(rendered)
        assert upgraded == {"brain-context": host["brain-context"], "custom": {"Stop": []}}
        assert self.render(template, rendered) == rendered

    def test_claude_merge_preserves_host_environment_and_permissions(self):
        template = "private_dot_claude/modify_private_settings.json"
        original = {
            "advisorModel": "opus",
            "teammateDefaultModel": "sonnet",
            "autoDreamEnabled": True,
            "skillListingMaxDescChars": 3000,
            "env": {
                "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1",
                "CLAUDE_CODE_FORCE_SESSION_PERSISTENCE": "0",
                "CUSTOM_SETTING": "preserved",
            },
            "permissions": {"deny": ["Read(./private)"], "additionalDirectories": ["/synthetic/host-root"]},
            "model": "host-model[1m]",
            "effortLevel": "xhigh",
            "remoteControlAtStartup": False,
        }
        rendered = self.render(template, json.dumps(original))
        data = json.loads(rendered)
        assert {"advisorModel", "teammateDefaultModel", "autoDreamEnabled", "skillListingMaxDescChars"} <= data.keys()
        assert data["env"]["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"] == "1"
        assert data["env"]["CUSTOM_SETTING"] == "preserved"
        assert data["env"]["CLAUDE_CODE_FORCE_SESSION_PERSISTENCE"] == "1"
        assert data["permissions"]["deny"] == ["Read(./private)"]
        assert data["env"]["DISABLE_UPDATES"] == "1"
        assert data["env"]["DISABLE_ERROR_REPORTING"] == "1"
        assert data["permissions"]["defaultMode"] == "bypassPermissions"
        assert data["syncClaudeAiSkills"] is False
        assert data["syncClaudeAiPlugins"] is False
        assert data["disableClaudeAiConnectors"] is True
        assert data["model"] == "host-model[1m]"
        assert data["effortLevel"] == "xhigh"
        assert data["remoteControlAtStartup"] is False
        assert data["permissions"]["additionalDirectories"] == ["/synthetic/host-root"]
        assert self.render(template, rendered) == rendered
        fresh = json.loads(self.render(template, ""))
        assert fresh["env"]["CLAUDE_CODE_FORCE_SESSION_PERSISTENCE"] == "1"
        assert fresh["model"] == "fable"
        assert fresh["remoteControlAtStartup"] is True
        # Opus 5.5 ignores the top-level effortLevel, so effort is seeded per model.
        assert "effortLevel" not in fresh
        assert fresh["modelSettings"]["claude-opus-5-5"] == {"effortLevel": "high"}
        seeded = json.loads(self.render(template, '{"modelSettings": {"claude-opus-5-5": {"effortLevel": "medium"}}}'))
        assert seeded["modelSettings"] == {
            "claude-opus-5-5": {"effortLevel": "medium"},
            "claude-fable-5-1": {"effortLevel": "high"},
            "claude-fable-5-2": {"effortLevel": "high"},
        }
        # dot trust owns permissions.additionalDirectories; host deny/additionalDirectories pass through untouched.
        assert fresh["permissions"] == {"defaultMode": "bypassPermissions"}

    def test_opencode_merge_preserves_custom_agents_and_provider_options(self):
        template = "dot_config/private_opencode/modify_private_opencode.json"
        original = {
            "agent": {"build": {"steps": 100, "prompt": "Host build instructions"}, "reviewer": {"steps": 20}},
            "compaction": {"reserved": 300000, "protect": ["skill"]},
            "experimental": {"batch_tool": True, "continue_loop_on_deny": True, "mcp_timeout": 120000},
            "model": "google-vertex/gemini-3.8-flash",
            "provider": {
                "google-vertex": {"options": {"timeout": 90000}},
                "openrouter": {"options": {"timeout": 60000}},
            },
        }
        rendered = self.render(template, json.dumps(original))
        data = json.loads(rendered)
        assert data["model"] == "google-vertex/gemini-3.8-flash"
        assert data["small_model"] == "openrouter/google/gemini-4-hydrogen"
        assert data["share"] == "disabled"
        assert data["autoupdate"] is False
        assert data["provider"]["openrouter"]["options"] == {"timeout": 60000}
        assert data["permission"] == "allow"
        assert data["agent"] == original["agent"]
        # 2.x dropped compaction.prune; replacing compaction retires it from deployed files.
        assert data["compaction"] == {"auto": True}
        assert data["formatter"] is True
        # OpenCode 2.x runs no language servers, so the repository no longer manages lsp.
        assert not {"instructions", "skills", "default_agent", "snapshot", "lsp"} & data.keys()
        assert data["experimental"] == original["experimental"]
        assert data["provider"]["google-vertex"]["options"]["timeout"] == 90000
        assert "policies" not in data
        assert self.render(template, rendered) == rendered
        fresh = json.loads(self.render(template, ""))
        assert fresh["model"] == "openrouter/google/gemini-4-hydrogen"
        assert fresh["small_model"] == "openrouter/google/gemini-4-hydrogen"

    def test_opencode_keeps_credentials_out_of_rendered_config(self):
        data = json.loads(
            self.render(
                "dot_config/private_opencode/modify_private_opencode.json",
                "{}",
                {"OPENROUTER_API_KEY": "synthetic-private-value", "GOOGLE_CLOUD_PROJECT": "unrelated"},
            )
        )
        assert "provider" not in data
        assert "synthetic-private-value" not in json.dumps(data)

    def test_opencode_cli_merge_preserves_client_preferences(self):
        template = "dot_config/private_opencode/modify_cli.json"
        original = {"keybinds": {"leader": "ctrl+a"}, "theme": {"mode": "dark"}, "scroll": {"speed": 2}}
        rendered = self.render(template, json.dumps(original))
        data = json.loads(rendered)
        assert data["$schema"] == "https://opencode.ai/v2/cli.json"
        assert data["theme"] == {"name": "fmind", "mode": "dark"}
        assert data["attention"] == {"notifications": False, "sound": False}
        assert data["keybinds"] == original["keybinds"]
        assert data["scroll"] == original["scroll"]
        assert self.render(template, rendered) == rendered

    def test_json_merge_preserves_mcp_and_unmanaged_hook_events(self):
        for template in [
            "private_dot_claude/modify_private_settings.json",
            "dot_config/private_opencode/modify_private_opencode.json",
        ]:
            with self.subTest(template=template):
                original = {
                    "mcp": {"custom-team": {"command": ["/synthetic/tool"]}},
                    "hooks": {"SessionStart": [{"command": "synthetic-context"}]},
                }
                rendered = self.render(template, json.dumps(original))
                data = json.loads(rendered)
                assert data["mcp"] == original["mcp"]
                assert data["hooks"]["SessionStart"] == original["hooks"]["SessionStart"]
                assert self.render(template, rendered) == rendered

    def test_copilot_merge_preserves_preferences_and_enforces_policy(self):
        template = "private_dot_copilot/modify_private_settings.json"
        original = {
            "model": "account-model",
            "effortLevel": "medium",
            "banner": "always",
            "notifications": True,
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
        assert data["banner"] == original["banner"]
        assert data["trusted_folders"] == []
        assert data["customOption"] is False
        assert data["notifications"] is False
        assert data["askUser"] is True
        assert data["autoUpdate"] is False
        assert data["includeCoAuthoredBy"] is False
        assert data["editorMode"] == "vim"
        assert self.render(template, rendered) == rendered
        fresh = json.loads(self.render(template, ""))
        assert fresh["model"] == "auto"
        assert fresh["effortLevel"] == "high"
        # Base-16 terminal colors follow the Ghostty palette.
        assert fresh["theme"] == "default"

    def test_antigravity_merge_preserves_account_and_explicit_empty_trust(self):
        template = "private_dot_gemini/private_antigravity-cli/modify_private_settings.json"
        original = {
            "model": "account-model",
            "gcp": {"project": "host-project", "location": "host-location", "extra": "preserved"},
            "permissions": {"allow": ["command(git)"], "ask": ["read_url(example.com)"], "deny": ["command(rm -rf)"]},
            "trustedWorkspaces": [],
            "pickerGrouping": "none",
            "runningLightSpeed": "slow",
            "colorScheme": "dark",
            "showFeedbackSurvey": True,
            "accountOption": False,
        }
        rendered = self.render(template, json.dumps(original))
        data = json.loads(rendered)
        for key, value in original.items():
            assert data[key] == value
        assert data["editorMode"] == "vim"
        # Off is agy's default and agy drops a false value on save, so managing it only drifts.
        assert "notifications" not in data
        assert data["queuedMessages"] == "send-immediately"
        assert data["verbosity"] == "high"
        display = str(self.home / ".gemini/antigravity-cli/display.py")
        for field, mode in [("statusLine", "statusline"), ("title", "title")]:
            assert data[field]["enabled"] is True
            assert shlex.split(data[field]["command"]) == ["exec", "python3", "-I", "-S", display, mode]
        assert self.render(template, rendered) == rendered
        fresh = json.loads(self.render(template, ""))
        assert fresh["pickerGrouping"] == "grouped"
        assert fresh["queuedMessages"] == "send-immediately"
        assert fresh["verbosity"] == "high"
        for key in ("model", "runningLightSpeed", "colorScheme", "showFeedbackSurvey"):
            assert key not in fresh
        assert "trustedWorkspaces" not in fresh  # dot trust owns folder trust.

    def test_remote_settings_preserve_host_identity_grants_and_projects(self):
        template = "private_dot_gemini/private_config/modify_private_config.json"
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
        assert grants["deny"] == ["command(rm *)"]
        assert data["customState"] == original["customState"]
        assert settings["autoExecutionPolicy"] == "CASCADE_COMMANDS_AUTO_EXECUTION_EAGER"
        assert settings["permissionPreset"] == "AGENT_PERMISSION_PRESET_TURBO"
        assert settings["artifactReviewMode"] == "ARTIFACT_REVIEW_MODE_TURBO"
        assert self.render(template, rendered) == rendered
        fresh = json.loads(self.render(template, ""))["userSettings"]
        assert "cliRemoteControlHostname" not in fresh
        assert "themeMode" not in fresh
        assert fresh["globalPermissionGrants"] == {"allow": managed}

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

    def test_json_merge_rejects_malformed_or_non_object_host_state(self):
        templates = (
            "private_dot_claude/modify_private_settings.json",
            "private_dot_copilot/modify_private_settings.json",
            "private_dot_gemini/private_antigravity-cli/modify_private_settings.json",
            "private_dot_gemini/private_config/modify_private_config.json",
            "private_dot_gemini/private_config/modify_private_hooks.json",
            "dot_config/private_opencode/modify_private_opencode.json",
            "dot_config/private_opencode/modify_cli.json",
            "private_dot_pi/private_agent/modify_private_settings.json",
        )
        for template in templates:
            for content in ['{"unfinished":', "[]", "null", '"string"']:
                with (
                    self.subTest(template=template, content=content),
                    pytest.raises(RuntimeError, match=r"chezmoi failed \(exit 1\)"),
                ):
                    self.render(template, content)

    def test_json_merge_returns_converged_host_bytes_and_keeps_large_integers(self):
        # Hook timeouts, feedbackSurveyRate, and Copilot's version are managed integers.
        template = "private_dot_claude/modify_private_settings.json"
        converged = json.loads(self.render(template, ""))
        converged["hostCounter"] = 9007199254740993
        host = json.dumps(dict(reversed(converged.items())), indent=4)
        assert self.render(template, host) == host
        drifted = json.loads(self.render(template, json.dumps({"hostCounter": 9007199254740993, "editorMode": "x"})))
        assert drifted["hostCounter"] == 9007199254740993
        assert drifted["editorMode"] == "vim"

    def test_native_jsonc_merges_preserve_comments_when_converged_and_keep_host_values(self):
        templates = [
            "private_dot_copilot/modify_private_settings.json",
            "dot_config/private_opencode/modify_private_opencode.json",
            "dot_config/private_opencode/modify_cli.json",
        ]
        assert json.loads(self.render(templates[0], ""))["connectors"] is False
        original = '{/* host preference */ "hostCounter":9007199254740993,"hostUrl":"https://example.com/a//b",}'
        for template in templates:
            with self.subTest(template=template):
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

    def test_opencode_native_parser_accepts_jsonc_before_and_after_managed_merge(self):
        opencode = native_binary("opencode")
        if opencode is None:
            pytest.skip("OpenCode native validation requires the workstation tool")
        target = self.home / ".config/opencode/opencode.json"
        target.parent.mkdir(parents=True)
        original = """{
          // Host-owned provider timeout, in OpenCode's supported JSONC format.
          "model": "openrouter/google/gemini-4-hydrogen",
          "provider": {"openrouter": {"options": {"timeout": 65432}}},
        }"""
        environment = {
            "HOME": str(self.home),
            "XDG_CONFIG_HOME": str(self.home / ".config"),
            "XDG_DATA_HOME": str(self.home / ".local/share"),
            "XDG_CACHE_HOME": str(self.home / ".cache"),
            "XDG_STATE_HOME": str(self.home / ".local/state"),
            "PATH": os.defpath,
            "LANG": "C.UTF-8",
        }
        # OpenCode 2.x answers through a server; --standalone runs a private one that exits with
        # the command, so the test never touches the workstation's background service.
        for content in (original, self.render("dot_config/private_opencode/modify_private_opencode.json", original)):
            target.write_text(content)
            result = subprocess.run(
                [opencode, "debug", "config", "--standalone"],
                env=environment,
                cwd=self.home,
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
            )
            # 2.x lists config sources and normalizes 1.x keys (provider.options -> providers.settings).
            [config] = [source["info"] for source in json.loads(result.stdout) if source.get("path") == str(target)]
            assert config["providers"]["openrouter"]["settings"]["timeout"] == 65432
            assert config["model"] == {"providerID": "openrouter", "model": "google/gemini-4-hydrogen"}

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
                # One call trusts the workspaces and this source directory, its path passed verbatim.
                assert log.read_text().splitlines() == ["trust", "all", str(source)]

    def test_toml_merge_returns_converged_host_bytes_and_keeps_large_integers(self):
        template = "dot_config/marimo/modify_private_marimo.toml"
        host = "# host comment\nhost_counter = 9007199254740993\n" + self.render(template, "")
        assert self.render(template, host) == host

    def test_marimo_vim_merge_preserves_host_settings_and_is_repeatable(self):
        template = "dot_config/marimo/modify_private_marimo.toml"
        original = '[keymap]\npreset = "default"\n[keymap.overrides]\ncustom = "Ctrl-Shift-K"\n[ai]\nmode = "manual"\n'
        for content in ["", original]:
            with self.subTest(content=content):
                rendered = self.render(template, content)
                data = tomllib.loads(rendered)
                assert data["keymap"]["preset"] == "vim"
                if content:
                    assert data["keymap"]["overrides"] == {"custom": "Ctrl-Shift-K"}
                    assert data["ai"] == {"mode": "manual"}
                assert self.render(template, rendered) == rendered

    def test_pi_extension_sets_google_vertex_location_without_notify_hooks(self):
        extension = (ROOT / "private_dot_pi/private_agent/extensions/google-vertex.ts").read_text(encoding="utf-8")
        assert 'pi.on("session_start"' in extension
        assert 'process.env.GOOGLE_CLOUD_LOCATION = "global"' in extension
        assert "agent_settled" not in extension
        assert "node:child_process" not in extension

    def test_zellij_config_uses_silent_attention_mode_and_validates_natively(self):
        config_path = ROOT / "dot_config/zellij/config.kdl"
        content = config_path.read_text(encoding="utf-8")
        assert 'host_notification_protocol "off"' in content
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

    def test_pi_dynamic_google_cloud_project_resolves_vertex_without_static_project(self):
        pi = native_binary("pi")
        if pi is None:
            pytest.skip("Pi native validation requires the workstation tool")
        agent_dir = self.home / ".pi/agent"
        (agent_dir / "extensions").mkdir(parents=True)
        (agent_dir / "settings.json").write_text(
            self.render("private_dot_pi/private_agent/modify_private_settings.json", '{"retry": {"enabled": false}}')
        )
        shutil.copyfile(
            ROOT / "private_dot_pi/private_agent/extensions/google-vertex.ts",
            agent_dir / "extensions/google-vertex.ts",
        )
        adc = self.home / "adc.json"
        adc.write_text("{}")
        base_env = {
            "HOME": str(self.home),
            "PATH": os.defpath,
            "LANG": "C.UTF-8",
            "PI_CODING_AGENT_DIR": str(agent_dir),
            "PI_OFFLINE": "1",
            "GOOGLE_APPLICATION_CREDENTIALS": str(adc),
            "HTTPS_PROXY": "http://127.0.0.1:1",
        }
        without_project = subprocess.run(
            [pi, "--mode", "json", "--no-session", "--no-tools", "-p", "hi"],
            env=base_env,
            cwd=self.home,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert "No API key found" in without_project.stderr

        with_project = subprocess.run(
            [pi, "--mode", "json", "--no-session", "--no-tools", "-p", "hi"],
            env={**base_env, "GOOGLE_CLOUD_PROJECT": "dynamic-fixture-project"},
            cwd=self.home,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        events = [json.loads(line) for line in with_project.stdout.splitlines() if line.startswith("{")]
        [reply] = [
            event["message"]
            for event in events
            if event.get("type") == "message_end" and event.get("message", {}).get("role") == "assistant"
        ]
        assert (reply["provider"], reply["model"], reply["thinkingLevel"]) == (
            "google-vertex",
            "gemini-4-argon",
            "high",
        )

        # A secondary provider's API key must not hijack defaultProvider or downgrade thinkingLevel.
        with_secondary = subprocess.run(
            [pi, "--mode", "json", "--no-session", "--no-tools", "-p", "hi"],
            env={**base_env, "GOOGLE_CLOUD_PROJECT": "dynamic-fixture-project", "OPENAI_API_KEY": "sk-synthetic"},
            cwd=self.home,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        secondary_events = [json.loads(line) for line in with_secondary.stdout.splitlines() if line.startswith("{")]
        [secondary_reply] = [
            event["message"]
            for event in secondary_events
            if event.get("type") == "message_end" and event.get("message", {}).get("role") == "assistant"
        ]
        assert (secondary_reply["provider"], secondary_reply["model"], secondary_reply["thinkingLevel"]) == (
            "google-vertex",
            "gemini-4-argon",
            "high",
        )

        # Resumed sessions keep their saved Vertex model and thinking level instead of resetting to defaults.
        saved_session = self.home / "resumed.jsonl"
        saved_session.write_text(
            "\n".join(
                json.dumps(entry)
                for entry in (
                    {
                        "type": "session",
                        "version": 3,
                        "id": "s1",
                        "timestamp": "2026-01-01T00:00:00.000Z",
                        "cwd": str(self.home),
                    },
                    {
                        "type": "model_change",
                        "id": "m1",
                        "parentId": None,
                        "timestamp": "2026-01-01T00:00:00.000Z",
                        "provider": "google-vertex",
                        "modelId": "gemini-3.8-flash",
                    },
                    {
                        "type": "thinking_level_change",
                        "id": "t1",
                        "parentId": "m1",
                        "timestamp": "2026-01-01T00:00:00.000Z",
                        "thinkingLevel": "low",
                    },
                    {
                        "type": "message",
                        "id": "u1",
                        "parentId": "t1",
                        "timestamp": "2026-01-01T00:00:01.000Z",
                        "message": {"role": "user", "content": "hi", "timestamp": 1767225601000},
                    },
                )
            )
            + "\n"
        )
        resumed = subprocess.run(
            [pi, "--mode", "json", "--session", str(saved_session), "--no-tools", "-p", "hi"],
            env={**base_env, "GOOGLE_CLOUD_PROJECT": "dynamic-fixture-project", "OPENAI_API_KEY": "sk-synthetic"},
            cwd=self.home,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        resumed_events = [json.loads(line) for line in resumed.stdout.splitlines() if line.startswith("{")]
        [resumed_reply] = [
            event["message"]
            for event in resumed_events
            if event.get("type") == "message_end" and event.get("message", {}).get("role") == "assistant"
        ]
        assert (resumed_reply["provider"], resumed_reply["model"], resumed_reply["thinkingLevel"]) == (
            "google-vertex",
            "gemini-3.8-flash",
            "low",
        )

        # Explicit --model flags take precedence over the configured defaultModel.
        explicit_model = subprocess.run(
            [pi, "--mode", "json", "--no-session", "--no-tools", "--model", "openai/gpt-4o", "-p", "hi"],
            env={**base_env, "GOOGLE_CLOUD_PROJECT": "dynamic-fixture-project", "OPENAI_API_KEY": "sk-synthetic"},
            cwd=self.home,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        explicit_events = [json.loads(line) for line in explicit_model.stdout.splitlines() if line.startswith("{")]
        [explicit_reply] = [
            event["message"]
            for event in explicit_events
            if event.get("type") == "message_end" and event.get("message", {}).get("role") == "assistant"
        ]
        assert (explicit_reply["provider"], explicit_reply["model"]) == ("openai", "gpt-4o")

    def test_pi_settings_seed_the_model_once_and_keep_host_state(self):
        template = "private_dot_pi/private_agent/modify_private_settings.json"
        fresh = json.loads(self.render(template, ""))
        assert fresh == {
            "$schema": "https://pi.dev/schemas/settings.schema.json",
            "collapseChangelog": True,
            "defaultModel": "gemini-4-argon",
            "defaultProvider": "google-vertex",
            "defaultThinkingLevel": "high",
            "enableAnalytics": False,
            "enableInstallTelemetry": False,
        }
        # Pi rewrites this file on /model and after an upgrade: its choices and bookkeeping survive apply.
        host = {
            "defaultProvider": "anthropic",
            "defaultModel": "host-model",
            "enableInstallTelemetry": True,
            "lastChangelogVersion": "1.5.0",
            "packages": ["npm:synthetic-package"],
        }
        merged = json.loads(self.render(template, json.dumps(host)))
        assert (merged["defaultProvider"], merged["defaultModel"], merged["defaultThinkingLevel"]) == (
            "anthropic",
            "host-model",
            "high",
        )
        assert merged["enableInstallTelemetry"] is False
        assert (merged["lastChangelogVersion"], merged["packages"]) == ("1.5.0", ["npm:synthetic-package"])
        rendered = self.render(template, json.dumps(merged, indent=2) + "\n")
        assert rendered == json.dumps(merged, indent=2) + "\n"

    def test_docker_merge_preserves_auths_and_contexts_while_managing_plugin_dirs(self):
        template = "private_dot_docker/modify_private_config.json"
        original = {"auths": {"https://index.docker.io/v1/": {}}, "currentContext": "colima"}
        rendered = self.render(template, json.dumps(original))
        data = json.loads(rendered)
        assert data["auths"] == original["auths"]
        assert data["currentContext"] == "colima"
        assert data["cliPluginsExtraDirs"] == [str(self.home / ".local/share/mise/shims")]
        assert self.render(template, rendered) == rendered
