"""Exercise chezmoi merges against synthetic host-owned MCP and hook settings."""

import json
import os
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class HarnessConfigTests(unittest.TestCase):
    temp: tempfile.TemporaryDirectory[str]
    home: Path
    config: Path
    chezmoi: str

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.config = self.home / "chezmoi.toml"
        self.config.write_text("")
        chezmoi = shutil.which("chezmoi")
        if chezmoi is None:
            raise RuntimeError("chezmoi is required for harness configuration tests")
        self.chezmoi = chezmoi

    def render(self, template: str, content: str, overrides: dict[str, str] | None = None) -> str:
        environment: dict[str, str] = dict(os.environ)
        environment["HOME"] = str(self.home)
        environment.pop("FKF_BASE", None)
        for name in ("OPENCODE_GCP_PROJECT", "GOOGLE_CLOUD_PROJECT", "VERTEX_LOCATION"):
            environment.pop(name, None)
        environment.update(overrides or {})
        # apply consumes the modify-template directive before rendering; execute-template
        # is lower level, so remove that directive to exercise the same template bytes.
        template_path = self.home / "input.tmpl"
        template_path.write_text((ROOT / template).read_text().split("\n", 1)[1])
        command: list[str] = [
            self.chezmoi,
            "--source",
            str(ROOT),
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

    def test_toml_merge_preserves_fkf_ownership_and_hooks(self):
        for harness in ["codex", "grok"]:
            with self.subTest(harness=harness):
                block = (
                    f"# >>> fkf harness {harness} fkf-brain\n"
                    '# base: "/synthetic/brain"\n'
                    '[mcp_servers.fkf-brain]\ncommand = "/synthetic/fkf"\n'
                    'args = ["mcp", "serve", "--base", "/synthetic/brain"]\n'
                    '\n[[hooks.SessionStart]]\nmatcher = "startup"\n'
                    '[[hooks.SessionStart.hooks]]\ntype = "command"\ncommand = "synthetic-hook"\n'
                    f"# <<< fkf harness {harness} fkf-brain\n"
                )
                original = 'custom = "preserved"\n\n' + block
                template = f"dot_{harness}/modify_private_config.toml"
                rendered = self.render(template, original)
                assert rendered.count(block) == 1
                data = tomllib.loads(rendered)
                assert data["custom"] == "preserved"
                assert data["mcp_servers"]["fkf-brain"]["command"] == "/synthetic/fkf"
                assert data["hooks"]["SessionStart"][0]["hooks"][0]["command"] == "synthetic-hook"
                assert "fkf" not in data["mcp_servers"]
                assert self.render(template, rendered) == rendered

    def test_codex_migration_keeps_autonomy_memory_and_native_subagents(self):
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
            "memories": True,
            "multi_agent_v2": True,
            "prevent_idle_sleep": True,
        }
        assert data["agents"] == {
            "job_max_runtime_seconds": 10800,
            "reviewer": {"description": "Host-owned reviewer"},
        }
        assert self.render(template, rendered) == rendered

    def test_grok_migration_removes_tuning_without_restoring_foreign_hooks(self):
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
        assert data["features"] == {"feedback": False, "lsp_tools": True, "telemetry": False}
        assert data["models"] == {"default_reasoning_effort": "xhigh"}
        assert data["ui"]["permission_mode"] == "always-approve"
        assert "fork_secondary_model" not in data["ui"]
        assert "yolo" not in data["ui"]
        assert data["compat"]["claude"]["hooks"] is False
        assert "sessions" not in data["compat"]["claude"]
        assert data["memory"]["enabled"] is True
        assert self.render(template, rendered) == rendered

    def test_claude_migration_preserves_host_environment_and_permissions(self):
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
        assert (
            not {"advisorModel", "teammateDefaultModel", "autoDreamEnabled", "skillListingMaxDescChars"} & data.keys()
        )
        assert "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS" not in data["env"]
        assert data["env"]["CUSTOM_SETTING"] == "preserved"
        assert data["permissions"]["deny"] == ["Read(./private)"]
        assert data["permissions"]["defaultMode"] == "bypassPermissions"
        assert data["autoMemoryEnabled"] is True
        assert self.render(template, rendered) == rendered

    def test_opencode_migration_preserves_custom_agents_and_provider_options(self):
        template = "dot_config/opencode/modify_opencode.json"
        original = {
            "agent": {"build": {"steps": 100, "prompt": "Host build instructions"}, "reviewer": {"steps": 20}},
            "compaction": {"reserved": 300000, "protect": ["skill"]},
            "experimental": {"batch_tool": True, "continue_loop_on_deny": True, "mcp_timeout": 120000},
            "provider": {"google-vertex": {"options": {"timeout": 90000}}},
        }
        rendered = self.render(template, json.dumps(original))
        data = json.loads(rendered)
        assert data["permission"] == "allow"
        assert data["agent"] == {"build": {"prompt": "Host build instructions"}, "reviewer": {"steps": 20}}
        assert data["compaction"] == {"protect": ["skill"], "prune": True}
        assert data["formatter"] is True
        assert data["lsp"] is True
        assert data["experimental"] == {}
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
                    "mcp": {"fkf-team": {"command": ["/synthetic/fkf"]}},
                    "hooks": {"SessionStart": [{"command": "synthetic-context"}]},
                }
                rendered = self.render(template, json.dumps(original))
                data = json.loads(rendered)
                assert data["mcp"] == original["mcp"]
                assert data["hooks"]["SessionStart"] == original["hooks"]["SessionStart"]
                assert self.render(template, rendered) == rendered

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

    def test_grok_vim_enables_prompt_and_scrollback_after_migration(self):
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


if __name__ == "__main__":
    unittest.main()
