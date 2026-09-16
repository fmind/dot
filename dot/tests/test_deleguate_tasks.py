"""Observable batch outcomes using local fake workers, never a paid provider."""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

RUNNER = Path(__file__).resolve().parents[2] / "skills/deleguate-tasks/scripts/run.py"


def task(root: Path, name: str, *, status: str = "SUCCESS", delay: float = 0.0) -> dict:
    workspace = root / name
    workspace.mkdir(exist_ok=True)
    code = (
        "import json,time,pathlib; "
        f"time.sleep({delay!r}); pathlib.Path('artifact').write_text('correct'); "
        f"print(json.dumps(dict(status={status!r},response='done',conversation_id='conversation-1')))"
    )
    return {
        "id": name,
        "workspace": str(workspace),
        "prompt": "do the task",
        "command": [sys.executable, "-c", code, "{prompt}"],
        "result_format": "agy-json",
        "checks": [
            [sys.executable, "-c", "from pathlib import Path; assert Path('artifact').read_text() == 'correct'"]
        ],
    }


def invoke(root: Path, tasks: list[dict], **options: object) -> tuple[subprocess.CompletedProcess, dict]:
    manifest = root / "batch.json"
    manifest.write_text(json.dumps({"tasks": tasks, **options}))
    result = subprocess.run(
        [sys.executable, str(RUNNER), str(manifest), "--state-dir", str(root / "state")],
        capture_output=True,
        text=True,
        timeout=20,
    )
    return result, json.loads(result.stdout or result.stderr)


def test_parallel_workers_then_verified_dependency(tmp_path: Path) -> None:
    first, second, third = [task(tmp_path, f"task-{i}", delay=0.15) for i in range(3)]
    third["depends_on"] = [first["id"], second["id"]]
    result, output = invoke(tmp_path, [first, second, third])
    assert result.returncode == 0
    assert [row["state"] for row in output["tasks"]] == ["verified"] * 3
    ledger = json.loads((Path(output["run"]) / "ledger.json").read_text())["tasks"]
    assert ledger["task-1"]["process"]["started_at"] < ledger["task-0"]["process"]["ended_at"]
    assert ledger["task-2"]["process"]["started_at"] > max(ledger[f"task-{i}"]["ended_at"] for i in (0, 1))
    assert ledger["task-0"]["conversation_id"] == "conversation-1"
    assert (Path(output["run"]) / "ledger.json").stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("status", ["ERROR", "WAITING", "RUNNING", "CANCELED", "INTERRUPTED", "INVALID"])
def test_zero_exit_is_not_provider_success(tmp_path: Path, status: str) -> None:
    first = task(tmp_path, "first", status=status)
    second = task(tmp_path, "second")
    second["depends_on"] = ["first"]
    result, output = invoke(tmp_path, [first, second])
    assert result.returncode == 1
    assert [t["state"] for t in output["tasks"]] == ["failed", "blocked"]
    assert not (tmp_path / "second/artifact").exists()


@pytest.mark.parametrize("failure", ["check", "no-check", "stderr", "malformed", "missing-executable", "timeout"])
def test_fail_closed_and_block_dependents(tmp_path: Path, failure: str) -> None:
    first = task(tmp_path, "first")
    if failure == "check":
        first["checks"] = [[sys.executable, "-c", "raise SystemExit(1)"]]
    elif failure == "no-check":
        first["checks"] = []
    elif failure == "stderr":
        first["command"][2] += "; import sys; sys.stderr.write('permission denied')"
    elif failure == "malformed":
        first["command"][2] = "print('not json')"
    elif failure == "missing-executable":
        first["command"][0] = str(tmp_path / "missing")
    else:
        first["command"][2] = "import time; time.sleep(30)"
    second = task(tmp_path, "second")
    second["depends_on"] = ["first"]
    result, output = invoke(tmp_path, [first, second], timeout=1)
    assert result.returncode == 1
    expected = "needs_review" if failure in {"no-check", "stderr"} else "failed"
    assert [t["state"] for t in output["tasks"]] == [expected, "blocked"]


def test_shared_workspace_serialized(tmp_path: Path) -> None:
    first, second = task(tmp_path, "first", delay=0.1), task(tmp_path, "second")
    second["workspace"] = first["workspace"]
    _, output = invoke(tmp_path, [first, second])
    ledger = json.loads((Path(output["run"]) / "ledger.json").read_text())["tasks"]
    assert ledger["second"]["process"]["started_at"] > ledger["first"]["ended_at"]


@pytest.mark.parametrize("mutation", ["cycle", "unknown", "duplicate", "type", "extra"])
def test_invalid_batch_does_not_launch(tmp_path: Path, mutation: str) -> None:
    first = task(tmp_path, "first")
    tasks = [first]
    if mutation in {"cycle", "unknown"}:
        first["depends_on"] = ["first" if mutation == "cycle" else "absent"]
    elif mutation == "duplicate":
        tasks.append(first)
    elif mutation == "type":
        first["checks"] = "not a command list"
    else:
        first["unexpected"] = True
    result, _ = invoke(tmp_path, tasks)
    assert result.returncode == 2
    assert not (tmp_path / "first/artifact").exists()
    assert not (tmp_path / "state").exists()


def test_cancellation_stops_descendants_and_queue(tmp_path: Path) -> None:
    first, second = task(tmp_path, "first"), task(tmp_path, "second")
    first["command"][2] = (
        "import subprocess,sys,time,pathlib; "
        "p=subprocess.Popen([sys.executable,'-c',\"import time,pathlib; time.sleep(2); pathlib.Path('leaked').touch()\"]); "
        "pathlib.Path('ready').touch(); time.sleep(30)"
    )
    manifest = tmp_path / "batch.json"
    manifest.write_text(json.dumps({"tasks": [first, second], "concurrency": 1}))
    with subprocess.Popen(
        [sys.executable, str(RUNNER), str(manifest), "--state-dir", str(tmp_path / "state")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as process:
        deadline = time.monotonic() + 5
        while not (tmp_path / "first/ready").exists():
            assert time.monotonic() < deadline
            time.sleep(0.02)
        os.kill(process.pid, signal.SIGTERM)
        stdout, _ = process.communicate(timeout=5)
    assert [t["state"] for t in json.loads(stdout)["tasks"]] == ["canceled", "canceled"]
    time.sleep(2.1)
    assert not (tmp_path / "first/leaked").exists()
    assert not (tmp_path / "second/artifact").exists()
