"""Exercise chezmoi merges against synthetic host-owned MCP and hook settings."""

import json
import os
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


def _strings(value: object) -> list[str]:
    if isinstance(value, dict):
        return [item for child in value.values() for item in _strings(child)]
    if isinstance(value, list):
        return [item for child in value for item in _strings(child)]
    return [value] if isinstance(value, str) else []


class HarnessConfigTests(unittest.TestCase):
    temp: tempfile.TemporaryDirectory[str]
    home: Path
    source: Path
    config: Path
    chezmoi: str

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
        chezmoi = shutil.which("chezmoi")
        if chezmoi is None:
            raise RuntimeError("chezmoi is required for harness configuration tests")
        self.chezmoi = chezmoi

    def render(self, template: str, content: str, overrides: dict[str, str] | None = None) -> str:
        environment: dict[str, str] = dict(os.environ)
        environment["HOME"] = str(self.home)
        for name in (
            "OPENCODE_GCP_PROJECT",
            "OPENROUTER_API_KEY",
            "GOOGLE_CLOUD_PROJECT",
            "VERTEX_LOCATION",
            "ANTIGRAVITY_CLOUD_PROJECT",
            "ANTIGRAVITY_CLOUD_LOCATION",
        ):
            environment.pop(name, None)
        environment.update(overrides or {})
        # apply consumes the modify-template directive before rendering; execute-template
        # is lower level, so remove that directive to exercise the same template bytes.
        template_path = self.home / "input.tmpl"
        template_path.write_text((ROOT / template).read_text().removeprefix("# chezmoi:modify-template\n"))
        command: list[str] = [
            self.chezmoi,
            "--source",
            str(self.source),
            "--destination",
            str(self.home),
            "--config",
            str(self.config),
            "execute-template",
            "--with-stdin",
            "--file",
            str(template_path),
        ]
        try:
            result = subprocess.run(
                command,
                input=content,
                encoding="utf-8",
                capture_output=True,
                check=True,
                env=environment,
            )
        except subprocess.CalledProcessError as err:
            raise RuntimeError(
                f"chezmoi execute-template failed (exit {err.returncode}):\nstdout: {err.stdout}\nstderr: {err.stderr}"
            ) from err
        return result.stdout

    def test_toml_merge_preserves_unmanaged_settings_and_is_repeatable(self):
        for harness in ["codex", "grok"]:
            with self.subTest(harness=harness):
                original = 'custom = "preserved"\n\n[mcp_servers.custom]\ncommand = "/synthetic/tool"\n'
                template = f"dot_{harness}/modify_private_config.toml"
                rendered = self.render(template, original)
                data = tomllib.loads(rendered)
                assert data["custom"] == "preserved"
                assert data["mcp_servers"]["custom"]["command"] == "/synthetic/tool"
                assert self.render(template, rendered) == rendered

    def test_codex_merge_keeps_autonomy_memory_and_native_subagents(self):
        template = "dot_codex/modify_private_config.toml"
        original = """
approval_policy = "on-request"
[features]
code_mode = { enabled = true }
concurrent_reasoning_summaries = true
context_management = true
deferred_executor = true
browser_use = true
[agents]
max_concurrent_threads_per_session = 4
default_subagent_reasoning_effort = "xhigh"
[agents.reviewer]
description = "Host-owned reviewer"
"""
        rendered = self.render(template, original)
        data = tomllib.loads(rendered)
        assert data["approval_policy"] == "never"
        assert data["sandbox_mode"] == "danger-full-access"
        assert data["features"] == {
            "browser_use": True,
            "code_mode": {"enabled": True},
            "concurrent_reasoning_summaries": True,
            "context_management": True,
            "deferred_executor": True,
            "memories": True,
            "multi_agent_v2": True,
            "prevent_idle_sleep": True,
        }
        assert data["agents"] == {
            "job_max_runtime_seconds": 10800,
            "max_concurrent_threads_per_session": 4,
            "default_subagent_reasoning_effort": "xhigh",
            "reviewer": {"description": "Host-owned reviewer"},
        }
        assert self.render(template, rendered) == rendered

    def test_grok_merge_preserves_unmanaged_tuning_and_disables_foreign_hooks(self):
        template = "dot_grok/modify_private_config.toml"
        original = """
[features]
two_pass_compaction = true
codebase_indexing = true
[models]
default = "old-model"
default_reasoning_effort = "xhigh"
max_retries = 8
[ui]
fork_secondary_model = "old-fork-model"
yolo = false
[compat.claude]
hooks = true
sessions = false
"""
        rendered = self.render(template, original)
        data = tomllib.loads(rendered)
        assert data["features"] == {
            "feedback": False,
            "lsp_tools": True,
            "telemetry": False,
            "two_pass_compaction": True,
            "codebase_indexing": True,
        }
        assert data["models"] == {"default_reasoning_effort": "xhigh", "default": "old-model", "max_retries": 8}
        assert data["ui"]["permission_mode"] == "always-approve"
        assert data["ui"]["fork_secondary_model"] == "old-fork-model"
        assert data["ui"]["yolo"] is False
        assert data["compat"]["claude"]["hooks"] is False
        assert data["compat"]["claude"]["sessions"] is False
        assert data["memory"]["enabled"] is True
        assert self.render(template, rendered) == rendered
        assert tomllib.loads(self.render(template, ""))["models"] == {"default_reasoning_effort": "high"}

    def test_claude_merge_preserves_host_environment_and_permissions(self):
        template = "dot_claude/modify_settings.json"
        original = {
            "advisorModel": "opus",
            "teammateDefaultModel": "sonnet",
            "autoDreamEnabled": True,
            "skillListingMaxDescChars": 3000,
            "env": {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1", "CUSTOM_SETTING": "preserved"},
            "permissions": {"deny": ["Read(./private)"], "additionalDirectories": ["/synthetic/host-root"]},
            "model": "host-model[1m]",
            "effortLevel": "xhigh",
            "enableAllProjectMcpServers": True,
        }
        rendered = self.render(template, json.dumps(original))
        data = json.loads(rendered)
        assert {"advisorModel", "teammateDefaultModel", "autoDreamEnabled", "skillListingMaxDescChars"} <= data.keys()
        assert data["env"]["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"] == "1"
        assert data["env"]["CUSTOM_SETTING"] == "preserved"
        assert data["permissions"]["deny"] == ["Read(./private)"]
        assert data["permissions"]["defaultMode"] == "bypassPermissions"
        assert data["autoMemoryEnabled"] is True
        assert data["model"] == "host-model[1m]"
        assert data["effortLevel"] == "xhigh"
        assert data["enableAllProjectMcpServers"] is False
        managed_roots = [str(self.home / name) for name in (".agents", ".local/share/chezmoi", "fmind")]
        assert data["permissions"]["additionalDirectories"][:4] == ["/synthetic/host-root", *managed_roots]
        assert self.render(template, rendered) == rendered
        fresh = json.loads(self.render(template, ""))
        assert fresh["model"] == "claude-fable-5-1[1m]"
        assert fresh["effortLevel"] == "high"
        assert fresh["permissions"]["additionalDirectories"][:3] == managed_roots
        with pytest.raises(RuntimeError, match="additionalDirectories must be an array"):
            self.render(template, '{"permissions": {"additionalDirectories": "/synthetic"}}')

    def test_opencode_merge_preserves_custom_agents_and_provider_options(self):
        template = "dot_config/opencode/modify_opencode.json"
        original = {
            "agent": {"build": {"steps": 100, "prompt": "Host build instructions"}, "reviewer": {"steps": 20}},
            "compaction": {"reserved": 300000, "protect": ["skill"]},
            "experimental": {"batch_tool": True, "continue_loop_on_deny": True, "mcp_timeout": 120000},
            "theme": "fmind",
            "model": "google-vertex/gemini-3.8-flash",
            "provider": {
                "google-vertex": {"options": {"timeout": 90000}},
                "openrouter": {"options": {"timeout": 60000}},
            },
        }
        rendered = self.render(template, json.dumps(original))
        data = json.loads(rendered)
        assert "theme" not in data
        assert data["model"] == "openrouter/google/gemini-3.8-flash"
        assert data["small_model"] == data["model"]
        assert data["default_agent"] == "build"
        assert data["share"] == "disabled"
        assert data["snapshot"] is True
        assert data["provider"]["openrouter"]["options"] == {"timeout": 60000}
        assert data["permission"] == "allow"
        assert data["agent"] == original["agent"]
        assert data["compaction"] == {"reserved": 300000, "protect": ["skill"], "auto": True, "prune": True}
        assert data["formatter"] is True
        assert data["lsp"] is True
        assert data["experimental"] == original["experimental"]
        assert data["provider"]["google-vertex"]["options"]["timeout"] == 90000
        assert self.render(template, rendered) == rendered

    def test_opencode_keeps_credentials_out_of_rendered_config(self):
        data = json.loads(
            self.render(
                "dot_config/opencode/modify_opencode.json",
                "{}",
                {"OPENROUTER_API_KEY": "synthetic-private-value", "GOOGLE_CLOUD_PROJECT": "unrelated"},
            )
        )
        assert "provider" not in data
        assert "synthetic-private-value" not in json.dumps(data)

    def test_opencode_retires_only_legacy_managed_credential(self):
        template = "dot_config/opencode/modify_opencode.json"
        for value in ("{env:OPENROUTER_API_KEY}", "{env:CUSTOMER_OPENROUTER_KEY}", "{file:/customer/token}"):
            original = {"provider": {"openrouter": {"options": {"apiKey": value, "timeout": 123}}}}
            rendered = self.render(template, json.dumps(original))
            options = json.loads(rendered)["provider"]["openrouter"]["options"]
            assert options["timeout"] == 123
            if value == "{env:OPENROUTER_API_KEY}":
                assert "apiKey" not in options
            else:
                assert options["apiKey"] == value
            assert self.render(template, rendered) == rendered

    def test_opencode_tui_merge_preserves_keyboard_preferences(self):
        template = "dot_config/opencode/modify_tui.json"
        original = {"keybinds": {"leader": "ctrl+a"}, "scroll_speed": 2}
        rendered = self.render(template, json.dumps(original))
        data = json.loads(rendered)
        assert data["theme"] == "fmind"
        assert data["keybinds"] == original["keybinds"]
        assert data["scroll_speed"] == 2
        assert self.render(template, rendered) == rendered

    def test_json_merge_preserves_mcp_and_unmanaged_hook_events(self):
        for template in ["dot_claude/modify_settings.json", "dot_config/opencode/modify_opencode.json"]:
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
        template = "dot_copilot/modify_settings.json"
        original = {
            "model": "account-model",
            "effortLevel": "medium",
            "banner": "always",
            "notifications": False,
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
        assert data["notifications"] is True
        assert data["autoUpdate"] is False
        assert data["includeCoAuthoredBy"] is False
        assert data["editorMode"] == "vim"
        assert self.render(template, rendered) == rendered
        fresh = json.loads(self.render(template, ""))
        assert fresh["model"] == "auto"
        assert fresh["effortLevel"] == "high"

    def test_antigravity_merge_preserves_account_and_explicit_empty_trust(self):
        template = "dot_gemini/antigravity-cli/modify_private_settings.json"
        original = {
            "model": "account-model",
            "gcp": {"project": "host-project", "location": "host-location", "extra": "preserved"},
            "trustedWorkspaces": [],
            "pickerGrouping": "flat",
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
        assert data["notifications"] is True
        assert self.render(template, rendered) == rendered
        fresh = json.loads(self.render(template, ""))
        for key in ("model", "pickerGrouping", "runningLightSpeed", "colorScheme", "showFeedbackSurvey"):
            assert key not in fresh
        assert "trustedWorkspaces" not in fresh  # dot trust owns folder trust.

    def test_remote_settings_preserve_host_identity_grants_and_projects(self):
        template = "dot_gemini/private_config/modify_private_config.json"
        original = {
            "userSettings": {
                "cliRemoteControlHostname": "fixture-host",
                "themeMode": "THEME_MODE_DARK",
                "globalPermissionGrants": {
                    "allow": ["read_file(/fixture)"],
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
        assert grants["allow"] == ["read_file(/fixture)", "read_url(*)", "execute_url(*)", "mcp(*)"]
        for action in ("ask", "deny"):
            assert grants[action] == original["userSettings"]["globalPermissionGrants"][action]
        assert data["customState"] == original["customState"]
        assert settings["autoExecutionPolicy"] == "CASCADE_COMMANDS_AUTO_EXECUTION_EAGER"
        assert settings["permissionPreset"] == "AGENT_PERMISSION_PRESET_TURBO"
        assert settings["artifactReviewMode"] == "ARTIFACT_REVIEW_MODE_TURBO"
        assert self.render(template, rendered) == rendered
        fresh = json.loads(self.render(template, ""))["userSettings"]
        assert "cliRemoteControlHostname" not in fresh
        assert "themeMode" not in fresh
        assert fresh["globalPermissionGrants"] == {"allow": ["read_url(*)", "execute_url(*)", "mcp(*)"]}

    def test_antigravity_cloud_override_is_explicit_and_json_safe(self):
        template = "dot_gemini/antigravity-cli/modify_private_settings.json"
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
        template = "dot_copilot/modify_lsp-config.json"
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
        for content in ['{"unfinished":', "[]", "null", '"string"']:
            with self.subTest(content=content), pytest.raises(RuntimeError, match="chezmoi execute-template failed"):
                self.render("dot_copilot/modify_settings.json", content)

    def test_json_merge_returns_converged_host_bytes_and_keeps_large_integers(self):
        # Hook timeouts, feedbackSurveyRate, and Copilot's version are managed integers.
        template = "dot_claude/modify_settings.json"
        converged = json.loads(self.render(template, ""))
        converged["hostCounter"] = 9007199254740993
        host = json.dumps(dict(reversed(converged.items())), indent=4)
        assert self.render(template, host) == host
        drifted = json.loads(self.render(template, json.dumps({"hostCounter": 9007199254740993, "editorMode": "x"})))
        assert drifted["hostCounter"] == 9007199254740993
        assert drifted["editorMode"] == "vim"
        legacy = json.dumps({"theme": "fmind", "hostCounter": 9007199254740993})
        migrated = json.loads(self.render("dot_config/opencode/modify_opencode.json", legacy))
        assert migrated["hostCounter"] == 9007199254740993

    def test_toml_merge_returns_converged_host_bytes_and_keeps_large_integers(self):
        template = "dot_codex/modify_private_config.toml"
        host = "# host comment\nhost_counter = 9007199254740993\n" + self.render(template, "")
        assert self.render(template, host) == host

    def test_gh_dash_commands_reach_repo_paths_with_spaces(self):
        self.home = self.home / "home with spaces"
        self.home.mkdir()
        data = yaml.safe_load(self.render("dot_config/gh-dash/config.yml.tmpl", ""))
        mappings = data["repoPaths"]
        assert mappings["fmind/dot"] == str(self.home / ".local/share/chezmoi")
        assert mappings[":owner/:repo"] == str(self.home / ":owner/:repo")
        binding = next(item["command"] for item in data["keybindings"]["prs"] if item["key"] == "O")
        for repo in ["fmind/dot", "synthetic/project"]:
            with self.subTest(repo=repo):
                owner, name = repo.split("/")
                path = mappings.get(repo, mappings[":owner/:repo"].replace(":owner", owner).replace(":repo", name))
                Path(path).mkdir(parents=True)
                # Observe the working directory reached by the native shell binding.
                command = binding.replace("{{.RepoPath}}", path).replace("&& lazygit", "&& pwd")
                result = subprocess.run(["sh", "-c", command], capture_output=True, text=True, check=True)
                assert result.stdout.strip() == path

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

    def test_grok_vim_enables_prompt_and_scrollback_after_merge(self):
        template = "dot_grok/modify_private_config.toml"
        rendered = self.render(template, "[ui]\nsimple_mode = true\nvim_mode = false\nscroll_speed = 20\n")
        data = tomllib.loads(rendered)
        assert data["ui"]["simple_mode"] is False
        assert data["ui"]["vim_mode"] is True
        assert data["ui"]["scroll_speed"] == 20
        assert self.render(template, rendered) == rendered

    def test_hooks_only_notify_and_clear_retired_capture_events(self):
        # Hooks name the CLI absolutely: a harness may start without ~/.local/bin on PATH.
        dot = str(self.home / ".local/bin/dot")
        retired = {"PreCompact": [], "SessionEnd": [], "SubagentStop": []}
        deployed = [{"hooks": [{"command": f"{dot} agent hook session codex", "type": "command"}], "matcher": ""}]

        codex_template = "dot_codex/modify_private_config.toml"
        codex = tomllib.loads(self.render(codex_template, ""))["hooks"]
        assert [hook["command"] for hook in codex["Stop"][0]["hooks"]] == [f"{dot} agent hook notify codex stop"]
        assert {event: codex[event] for event in retired} == retired
        # The merge never deletes keys: managed empty lists replace deployed capture hooks.
        stale = "".join(
            f'[[hooks.{event}]]\nmatcher = ""\n[[hooks.{event}.hooks]]\ncommand = "{dot} agent hook session codex"\n'
            for event in retired
        )
        assert {
            event: tomllib.loads(self.render(codex_template, stale))["hooks"][event] for event in retired
        } == retired

        claude_template = "dot_claude/modify_settings.json"
        claude = json.loads(self.render(claude_template, "{}"))["hooks"]
        assert [hook["command"] for hook in claude["Stop"][0]["hooks"]] == [f"{dot} agent hook notify claude stop"]
        assert [hook["command"] for hook in claude["Notification"][0]["hooks"]] == [
            f"{dot} agent hook notify claude needs-input"
        ]
        stale_claude = json.dumps({"hooks": dict.fromkeys(retired, deployed)})
        merged = json.loads(self.render(claude_template, stale_claude))["hooks"]
        assert {event: merged[event] for event in retired} == retired

        grok = json.loads(self.render("dot_grok/hooks/hooks.json.tmpl", ""))["hooks"]
        assert set(grok) == {"Notification", "Stop"}
        assert [hook["command"] for hook in grok["Stop"][0]["hooks"]] == [f"{dot} agent hook notify grok stop"]

        agy = json.loads(self.render("dot_gemini/private_config/private_hooks.json.tmpl", ""))
        assert set(agy) == {"notify"}
        copilot = json.loads(self.render("dot_copilot/hooks/session-log.json.tmpl", ""))
        assert set(copilot["hooks"]) == {"agentStop"}
        assert [hook["bash"] for hook in copilot["hooks"]["agentStop"]] == [f"{dot} agent hook notify copilot stop"]

        # Every hook notifies and names the CLI absolutely; none relies on PATH order.
        commands = [
            value
            for config in (codex, claude, grok, agy, copilot)
            for value in _strings(config)
            if " agent hook " in value
        ]
        assert len(commands) == 7
        assert all(command.startswith(f"{dot} agent hook notify ") for command in commands)

    def test_hook_commands_reject_home_directories_that_need_shell_quoting(self):
        self.home = self.home / "home with spaces"
        self.home.mkdir()
        for template in [
            "dot_claude/modify_settings.json",
            "dot_codex/modify_private_config.toml",
            "dot_grok/hooks/hooks.json.tmpl",
            "dot_gemini/private_config/private_hooks.json.tmpl",
            "dot_copilot/hooks/session-log.json.tmpl",
        ]:
            with self.subTest(template=template), pytest.raises(RuntimeError, match="not shell-safe"):
                self.render(template, "")
