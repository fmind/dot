"""Exercise the on-demand review task with a fake CLI, without model calls."""

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("output", "exit_code", "expected"),
    [
        ({"status": "SUCCESS", "structured_output": {"findings": []}, "usage": {"total_tokens": 123}}, 0, 0),
        ({"status": "ERROR", "error": "synthetic failure"}, 0, 1),
        ({"status": "SUCCESS", "structured_output": {"findings": []}}, 3, 3),
        ({"status": "SUCCESS"}, 0, 1),
        ("not JSON", 0, 1),
    ],
)
def test_review_keeps_native_failures_and_rejects_incomplete_results(
    tmp_path: Path, output: object, exit_code: int, expected: int
) -> None:
    native = tmp_path / "agy"
    native.write_text(
        f"#!{sys.executable}\n"
        "import json,os,sys\n"
        "from pathlib import Path\n"
        "Path(os.environ['AGY_TEST_ARGS']).write_text(json.dumps(sys.argv[1:]))\n"
        "print(os.environ['AGY_TEST_OUTPUT'])\n"
        "sys.stderr.write('native diagnostics\\n')\n"
        "sys.exit(int(os.environ['AGY_TEST_EXIT']))\n"
    )
    native.chmod(0o700)
    arguments = tmp_path / "arguments.json"
    environment = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "AGY_TEST_ARGS": str(arguments),
        "AGY_TEST_OUTPUT": json.dumps(output) if isinstance(output, dict) else str(output),
        "AGY_TEST_EXIT": str(exit_code),
    }
    task = tomllib.loads((ROOT / "mise.toml").read_text())["tasks"]["review:agy"]
    command = task["run"].replace("{{config_root}}", str(ROOT))
    result = subprocess.run(
        ["bash", "-c", command],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert (result.returncode == 0) == (expected == 0), result.stderr
    if expected == 3:
        assert result.returncode == 3
    assert "native diagnostics" in result.stderr
    args = json.loads(arguments.read_text())
    assert args[:6] == ["--agent", "code-reviewer", "--print-timeout", "20m", "--output-format", "json"]
    assert Path(args[7]).is_file()
    assert "Do not edit files" in args[-1]
    if expected == 0:
        assert json.loads(result.stdout) == output
