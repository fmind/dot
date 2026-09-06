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

    def render(self, template: str, content: str) -> str:
        environment: dict[str, str] = dict(os.environ)
        environment["HOME"] = str(self.home)
        environment.pop("FKF_BASE", None)
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

    def test_json_merge_preserves_mcp_and_unmanaged_hook_events(self):
        for template in ["dot_claude/modify_settings.json"]:
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


if __name__ == "__main__":
    unittest.main()
