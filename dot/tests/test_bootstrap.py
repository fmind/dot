from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import TypedDict, cast

ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "install.sh"


class ToolCall(TypedDict):
    tool: str
    args: list[str]


FAKE_TOOL = """#!{python}
import json
import os
from pathlib import Path
import sys

tool = Path(sys.argv[0]).name
args = sys.argv[1:]
with Path(os.environ["BOOTSTRAP_LOG"]).open("a", encoding="utf-8") as stream:
    stream.write(json.dumps({{"tool": tool, "args": args}}) + "\\n")

if tool == "mise" and args == ["--version"]:
    print(os.environ["FAKE_MISE_VERSION"] + " fixture")
elif tool == "chezmoi" and "https://github.com/fmind/dot.git" in args:
    source = Path(args[args.index("--source") + 1])
    source.mkdir(parents=True)
elif tool == "curl":
    raise SystemExit(99)
"""


class BootstrapFixture:
    def __init__(self, root: Path, mise_version: str) -> None:
        self.home = root / "home"
        self.bin = root / "bin"
        self.log = root / "calls.jsonl"
        self.source = self.home / ".local" / "share" / "chezmoi"
        self.bin.mkdir(parents=True)
        for name in ("chezmoi", "curl", "git", "mise"):
            executable = self.bin / name
            executable.write_text(FAKE_TOOL.format(python=sys.executable), encoding="utf-8")
            executable.chmod(0o755)
        self.environment = {
            "BOOTSTRAP_LOG": str(self.log),
            "CI": "true",
            "FAKE_MISE_VERSION": mise_version,
            "HOME": str(self.home),
            "LANG": "C.UTF-8",
            "PATH": f"{self.bin}{os.pathsep}/usr/bin{os.pathsep}/bin",
            "SKIP_GIT_PULL": "true",
        }

    def run(self) -> subprocess.CompletedProcess[str]:
        bash = shutil.which("bash")
        if bash is None:
            raise AssertionError("bash must be installed")
        return subprocess.run(
            [bash, str(INSTALLER)],
            env=self.environment,
            check=False,
            capture_output=True,
            text=True,
        )

    def calls(self) -> list[ToolCall]:
        if not self.log.exists():
            return []
        return [cast(ToolCall, json.loads(line)) for line in self.log.read_text(encoding="utf-8").splitlines()]


class BootstrapTest(unittest.TestCase):
    def test_unsupported_mise_fails_before_repository_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = BootstrapFixture(Path(directory), "2025.1.0")
            result = fixture.run()

            assert result.returncode != 0
            assert "mise 2026.9.1 or newer is required" in result.stderr
            assert fixture.calls() == [{"tool": "mise", "args": ["--version"]}]
            assert not fixture.source.exists()

    def test_first_install_and_rerun_use_the_bounded_task_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = BootstrapFixture(Path(directory), "2026.9.1")
            first = fixture.run()
            second = fixture.run()

            assert first.returncode == 0, first.stdout + first.stderr
            assert second.returncode == 0, second.stdout + second.stderr
            source = str(fixture.source)
            expected = [
                {"tool": "mise", "args": ["--version"]},
                {
                    "tool": "chezmoi",
                    "args": ["init", "--force", "https://github.com/fmind/dot.git", "--source", source],
                },
                {"tool": "mise", "args": ["trust", "-y", f"{source}/mise.toml"]},
                {"tool": "mise", "args": ["-C", source, "run", "install"]},
                {"tool": "mise", "args": ["--version"]},
                {"tool": "chezmoi", "args": ["init", "--force", "--source", source]},
                {"tool": "mise", "args": ["trust", "-y", f"{source}/mise.toml"]},
                {"tool": "mise", "args": ["-C", source, "run", "install"]},
            ]
            assert fixture.calls() == expected
            assert not (fixture.home / ".config" / "chezmoi" / "key.txt").exists()


if __name__ == "__main__":
    unittest.main()
