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
        template_path.write_text((ROOT / template).read_text().split("\n", 1)[1])
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

    def test_claude_merge_preserves_host_environment_and_permissions(self):
        template = "dot_claude/modify_settings.json"
        original = {
            "advisorModel": "opus",
            "teammateDefaultModel": "sonnet",
            "autoDreamEnabled": True,
            "skillListingMaxDescChars": 3000,
            "env": {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1", "CUSTOM_SETTING": "preserved"},
            "permissions": {"deny": ["Read(./private)"]},
        }
        rendered = self.render(template, json.dumps(original))
        data = json.loads(rendered)
        assert {"advisorModel", "teammateDefaultModel", "autoDreamEnabled", "skillListingMaxDescChars"} <= data.keys()
        assert data["env"]["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"] == "1"
        assert data["env"]["CUSTOM_SETTING"] == "preserved"
        assert data["permissions"]["deny"] == ["Read(./private)"]
        assert data["permissions"]["defaultMode"] == "bypassPermissions"
        assert data["autoMemoryEnabled"] is True
        assert self.render(template, rendered) == rendered

    def test_opencode_merge_preserves_custom_agents_and_provider_options(self):
        template = "dot_config/opencode/modify_opencode.json"
        original = {
            "agent": {"build": {"steps": 100, "prompt": "Host build instructions"}, "reviewer": {"steps": 20}},
            "compaction": {"reserved": 300000, "protect": ["skill"]},
            "experimental": {"batch_tool": True, "continue_loop_on_deny": True, "mcp_timeout": 120000},
            "provider": {"google-vertex": {"options": {"timeout": 90000}}},
        }
        rendered = self.render(template, json.dumps(original))
        data = json.loads(rendered)
        assert data["theme"] == "fmind"
        assert data["permission"] == "allow"
        assert data["agent"] == original["agent"]
        assert data["compaction"] == {"reserved": 300000, "protect": ["skill"], "prune": True}
        assert data["formatter"] is True
        assert data["lsp"] is True
        assert data["experimental"] == original["experimental"]
        assert data["provider"]["google-vertex"]["options"]["timeout"] == 90000
        assert self.render(template, rendered) == rendered

    def test_opencode_project_and_location_precedence(self):
        template = "dot_config/opencode/modify_opencode.json"
        cases = [
            ({}, "{env:OPENCODE_GCP_PROJECT}", "global"),
            ({"GOOGLE_CLOUD_PROJECT": "fallback"}, "fallback", "global"),
            (
                {"GOOGLE_CLOUD_PROJECT": "fallback", "OPENCODE_GCP_PROJECT": "explicit", "VERTEX_LOCATION": "region"},
                "explicit",
                "region",
            ),
        ]
        for environment, project, location in cases:
            with self.subTest(environment=environment):
                data = json.loads(self.render(template, "{}", environment))
                assert data["provider"]["google-vertex"]["options"] == {"project": project, "location": location}

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
        assert fresh["effortLevel"] == "xhigh"

    def test_antigravity_merge_preserves_account_and_explicit_empty_trust(self):
        template = "dot_gemini/antigravity-cli/modify_settings.json"
        original = {
            "model": "account-model",
            "gcp": {"project": "host-project", "location": "host-location", "extra": "preserved"},
            "trustedWorkspaces": [],
            "pickerGrouping": "flat",
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
        assert fresh["model"] == "Gemini 3.8 Flash (High)"
        assert fresh["trustedWorkspaces"] == [str(self.home), str(self.home / ".local/share/chezmoi")]

    def test_remote_settings_preserve_host_identity_grants_and_projects(self):
        template = "dot_gemini/private_config/modify_private_config.json"
        original = {
            "userSettings": {
                "cliRemoteControlHostname": "fixture-host",
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
        assert fresh["globalPermissionGrants"] == {"allow": ["read_url(*)", "execute_url(*)", "mcp(*)"]}

    def test_remote_model_selection_preserves_native_state(self):
        template = "dot_gemini/antigravity-cli/modify_private_antigravity_state.pbtxt"
        selected = "last_selected_agent_model: MODEL_PLACEHOLDER_M318\n"
        original = 'post_onboarding: { completed_steps: 1 }\ninstallation_uuid: "fixture"\n'
        for content in (original, original.rstrip(), original + "last_selected_agent_model: 123\n"):
            rendered = self.render(template, content)
            assert rendered == original + selected
            assert self.render(template, rendered) == rendered
        assert self.render(template, "") == selected

    def test_antigravity_cloud_override_is_explicit_and_json_safe(self):
        template = "dot_gemini/antigravity-cli/modify_settings.json"
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

    def test_capture_hooks_use_one_command_at_durable_boundaries(self):
        codex = tomllib.loads(self.render("dot_codex/modify_private_config.toml", ""))["hooks"]
        assert [hook["command"] for hook in codex["PreCompact"][0]["hooks"]] == ["dot agent hook session codex"]
        assert [hook["command"] for hook in codex["SessionEnd"][0]["hooks"]] == ["dot agent hook session codex"]
        assert [hook["command"] for hook in codex["Stop"][0]["hooks"]] == ["dot agent hook notify codex stop"]

        claude = json.loads(self.render("dot_claude/modify_settings.json", "{}"))["hooks"]
        assert [hook["command"] for hook in claude["PreCompact"][0]["hooks"]] == ["dot agent hook session claude"]
        assert [hook["command"] for hook in claude["SessionEnd"][0]["hooks"]] == ["dot agent hook session claude"]
        assert [hook["command"] for hook in claude["Stop"][0]["hooks"]] == ["dot agent hook notify claude stop"]
        assert [hook["command"] for hook in claude["SubagentStop"][0]["hooks"]] == ["dot agent hook session claude"]

        grok = json.loads((ROOT / "dot_grok/hooks/hooks.json").read_text())["hooks"]
        assert [hook["command"] for hook in grok["Stop"][0]["hooks"]] == ["dot agent hook notify grok stop"]
        assert all("hook usage" not in json.dumps(value) for value in (codex, claude, grok))

        agy = json.loads((ROOT / "dot_gemini/private_config/private_hooks.json").read_text())
        assert set(agy) == {"notify", "session-log"}
        copilot = json.loads((ROOT / "dot_copilot/hooks/session-log.json").read_text())
        assert [hook["bash"] for hook in copilot["hooks"]["sessionEnd"]] == ["dot agent hook copilot-session-end"]


class CursorConfigTests(HarnessConfigTests):
    def test_cursor_preserves_account_model_and_explicit_denials(self) -> None:
        original = json.dumps(
            {
                "model": {"id": "account-model"},
                "permissions": {"deny": ["Shell(rm)"]},
                "mcpServers": {"local": {"command": "fixture"}},
            }
        )
        result = self.render("dot_cursor/modify_private_cli-config.json", original)
        config = json.loads(result)
        assert config["model"] == {"id": "account-model"}
        assert config["permissions"]["deny"] == ["Shell(rm)"]
        assert config["approvalMode"] == "unrestricted"
        assert config["sandbox"]["mode"] == "disabled"
        assert config["editor"]["vimMode"]
        assert not config["attribution"]["attributeCommitsToAgent"]
        assert self.render("dot_cursor/modify_private_cli-config.json", result) == result
        fresh = json.loads(self.render("dot_cursor/modify_private_cli-config.json", ""))
        assert fresh["permissions"]["deny"] == []
        partial = json.loads(self.render("dot_cursor/modify_private_cli-config.json", '{"permissions": {"allow": []}}'))
        assert partial["permissions"]["deny"] == []

    def test_cursor_persona_hook_outputs_json_and_preserves_other_events(self) -> None:
        original = json.dumps(
            {"version": 1, "hooks": {"stop": [{"command": "fixture"}], "sessionStart": [{"command": "existing-hook"}]}}
        )
        rendered = self.render("dot_cursor/modify_hooks.json", original)
        config = json.loads(rendered)
        assert config["hooks"]["stop"] == [{"command": "fixture"}]
        assert config["hooks"]["sessionStart"][0]["command"] == "existing-hook"
        command = config["hooks"]["sessionStart"][1]["command"]
        persona = self.home / ".agents/AGENTS.md"
        persona.parent.mkdir()
        persona.write_text('Synthetic persona with "quotes" and\na newline.')
        result = subprocess.run(
            ["bash", "-c", command],
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "HOME": str(self.home)},
        )
        assert json.loads(result.stdout) == {"additional_context": persona.read_text()}
        assert self.render("dot_cursor/modify_hooks.json", rendered) == rendered
