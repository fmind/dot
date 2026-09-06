"""Exercise chezmoi merges against synthetic host-owned MCP and hook settings."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[1]


class HarnessConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.config = self.home / "chezmoi.toml"
        self.config.write_text("")
        self.chezmoi = shutil.which("chezmoi")
        self.assertIsNotNone(self.chezmoi)

    def render(self, template, content):
        environment = {**os.environ, "HOME": str(self.home)}
        environment.pop("FKF_BASE", None)
        # apply consumes the modify-template directive before rendering; execute-template
        # is lower level, so remove that directive to exercise the same template bytes.
        template_path = self.home / "input.tmpl"
        template_path.write_text((ROOT / template).read_text().split("\n", 1)[1])
        result = subprocess.run(
            [
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
            ],
            input=content,
            text=True,
            capture_output=True,
            check=True,
            env=environment,
        )
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
                self.assertEqual(rendered.count(block), 1)
                data = tomllib.loads(rendered)
                self.assertEqual(data["custom"], "preserved")
                self.assertEqual(data["mcp_servers"]["fkf-brain"]["command"], "/synthetic/fkf")
                self.assertEqual(data["hooks"]["SessionStart"][0]["hooks"][0]["command"], "synthetic-hook")
                self.assertNotIn("fkf", data["mcp_servers"])
                self.assertEqual(self.render(template, rendered), rendered)

    def test_json_merge_preserves_mcp_and_unmanaged_hook_events(self):
        for template in ["dot_claude/modify_settings.json", "dot_config/opencode/modify_opencode.json"]:
            with self.subTest(template=template):
                original = {
                    "mcp": {"fkf-team": {"command": ["/synthetic/fkf"]}},
                    "hooks": {"SessionStart": [{"command": "synthetic-context"}]},
                }
                rendered = self.render(template, json.dumps(original))
                data = json.loads(rendered)
                self.assertEqual(data["mcp"], original["mcp"])
                self.assertEqual(data["hooks"]["SessionStart"], original["hooks"]["SessionStart"])
                self.assertEqual(self.render(template, rendered), rendered)


if __name__ == "__main__":
    unittest.main()
