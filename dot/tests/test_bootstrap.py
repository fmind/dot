from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import TypedDict, cast

import yaml

ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "install.sh"
# A hung bootstrap must fail its own test instead of consuming the CI job limit.
TIMEOUT_SECONDS = 60


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
elif tool == "curl" and "FAKE_MISE_STOCK" in os.environ:
    # Stand in for https://mise.run: the piped script records the requested release.
    print('printf "%s" "${{MISE_VERSION:-}}" > "$BOOTSTRAP_LOG.requested"')
    print('mkdir -p "$HOME/.local/bin" && cp "$FAKE_MISE_STOCK" "$HOME/.local/bin/mise"')
elif tool == "curl":
    raise SystemExit(99)
"""


def pinned_mise_version() -> str:
    match = re.search(r'^MINIMUM_MISE_VERSION="([0-9.]+)"$', INSTALLER.read_text(encoding="utf-8"), re.MULTILINE)
    assert match is not None
    return match.group(1)


class BootstrapFixture:
    def __init__(self, root: Path, mise_version: str, *, mise_installed: bool = True) -> None:
        self.home = root / "home"
        self.bin = root / "bin"
        self.log = root / "calls.jsonl"
        self.source = self.home / ".local" / "share" / "chezmoi"
        self.bin.mkdir(parents=True)
        stock = root / "stock"
        stock.mkdir()
        for name in ("chezmoi", "curl", "git", "mise"):
            executable = (self.bin if mise_installed or name != "mise" else stock) / name
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
        if not mise_installed:
            self.environment["FAKE_MISE_STOCK"] = str(stock / "mise")

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
            timeout=TIMEOUT_SECONDS,
        )

    def calls(self) -> list[ToolCall]:
        if not self.log.exists():
            return []
        return [cast(ToolCall, json.loads(line)) for line in self.log.read_text(encoding="utf-8").splitlines()]


class BootstrapTest(unittest.TestCase):
    def test_unsupported_mise_fails_before_repository_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = BootstrapFixture(Path(directory), "2026.9.1")
            result = fixture.run()

            assert result.returncode != 0
            assert "mise 2026.9.10 or newer is required" in result.stderr
            assert fixture.calls() == [{"tool": "mise", "args": ["--version"]}]
            assert not fixture.source.exists()

    def test_first_install_and_rerun_use_the_bounded_task_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = BootstrapFixture(Path(directory), "2026.9.10")
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

    def test_missing_mise_is_installed_at_the_tested_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = BootstrapFixture(Path(directory), pinned_mise_version(), mise_installed=False)
            result = fixture.run()

            assert result.returncode == 0, result.stdout + result.stderr
            requested = Path(f"{fixture.log}.requested").read_text(encoding="utf-8")
            assert requested == f"v{pinned_mise_version()}"
            assert [call["tool"] for call in fixture.calls()[:2]] == ["curl", "mise"]

    def test_every_copy_of_the_mise_version_agrees(self) -> None:
        copies = {"install.sh": pinned_mise_version()}
        for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
            workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
            for name, job in workflow["jobs"].items():
                for step in job["steps"]:
                    if step.get("uses", "").startswith("jdx/mise-action@"):
                        # An unpinned action would install the latest mise, not the tested one.
                        copies[f"{path.name}:{name}"] = str(step.get("with", {}).get("version"))
        readme = re.search(r"requires mise ([0-9.]+[0-9])", (ROOT / "README.md").read_text(encoding="utf-8"))
        assert readme is not None
        copies["README.md"] = readme.group(1)

        assert len(copies) >= 5
        assert set(copies.values()) == {pinned_mise_version()}, copies
