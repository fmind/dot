#!/usr/bin/env python3
"""Run an authorized task batch; keep worker transcripts outside the coordinator context."""

import argparse
import asyncio
import contextlib
import json
import os
import re
import signal
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def now() -> str:
    return datetime.now(UTC).isoformat()


def write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def strings(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(x, str) and x and "\0" not in x for x in value)


def validate(spec: Any) -> dict[str, Any]:
    """Reject the complete batch before launching any task."""
    if not isinstance(spec, dict) or set(spec) - {"tasks", "concurrency", "timeout"}:
        raise ValueError("Batch must contain tasks, with optional concurrency and timeout.")
    for key, default, maximum in (("concurrency", 2, 16), ("timeout", 900, 86400)):
        value = spec.setdefault(key, default)
        if type(value) is not int or not 1 <= value <= maximum:
            raise ValueError(f"{key} must be an integer between 1 and {maximum}.")
    tasks = spec.get("tasks")
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= 100:
        raise ValueError("tasks must contain 1-100 task objects.")
    ids: set[str] = set()
    for task in tasks:
        if not isinstance(task, dict) or set(task) - {
            "id",
            "workspace",
            "prompt",
            "depends_on",
            "checks",
            "model",
            "effort",
            "add_dirs",
            "conversation_id",
            "command",
            "result_format",
        }:
            raise ValueError("Task contains unknown fields; see tracking.md.")
        identifier = task.get("id")
        if (
            not isinstance(identifier, str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", identifier)
            or identifier in ids
        ):
            raise ValueError("Task IDs must be unique lowercase names with optional digits/hyphens.")
        ids.add(identifier)
        for key in ("workspace", "prompt"):
            if not isinstance(task.get(key), str) or not task[key].strip() or "\0" in task[key]:
                raise ValueError(f"Task {identifier}: {key} must be nonempty text.")
        for key in ("depends_on", "add_dirs"):
            if not strings(task.setdefault(key, [])):
                raise ValueError(f"Task {identifier}: {key} must be a string list.")
        task["workspace"] = str(Path(task["workspace"]).expanduser().resolve())
        task["add_dirs"] = [str(Path(p).expanduser().resolve()) for p in task["add_dirs"]]
        if any(not Path(p).is_dir() for p in [task["workspace"], *task["add_dirs"]]):
            raise ValueError(f"Task {identifier}: all workspace directories must exist.")
        checks = task.setdefault("checks", [])
        if not isinstance(checks, list) or any(not strings(c) or not c for c in checks):
            raise ValueError(f"Task {identifier}: checks must be nonempty argument lists.")
        if "command" in task:
            if not strings(task["command"]) or sum(a == "{prompt}" for a in task["command"]) != 1:
                raise ValueError(f"Task {identifier}: command needs exactly one standalone {{prompt}} argument.")
            if any(k in task for k in ("model", "effort", "add_dirs", "conversation_id") if task.get(k)):
                raise ValueError(f"Task {identifier}: put custom harness options in command.")
        else:
            task.setdefault("model", "gemini-3.8-flash-high")
            task.setdefault("effort", "high")
            if not isinstance(task["model"], str) or not re.fullmatch(r"[a-zA-Z0-9._-]+", task["model"]):
                raise ValueError(f"Task {identifier}: invalid model slug.")
            if task["effort"] not in ("low", "medium", "high"):
                raise ValueError(f"Task {identifier}: invalid effort.")
            if "conversation_id" in task and (
                not isinstance(task["conversation_id"], str)
                or not re.fullmatch(r"[a-zA-Z0-9-]+", task["conversation_id"])
            ):
                raise ValueError(f"Task {identifier}: invalid conversation ID.")
        task.setdefault("result_format", "text" if "command" in task else "agy-json")
        if task["result_format"] not in ("text", "agy-json") or (
            "command" not in task and task["result_format"] != "agy-json"
        ):
            raise ValueError(f"Task {identifier}: invalid result_format.")
    remaining = {t["id"]: set(t["depends_on"]) for t in tasks}
    done: set[str] = set()
    while remaining:
        ready = {key for key, deps in remaining.items() if deps <= done}
        if not ready:
            raise ValueError("Dependencies contain a cycle or an unknown task ID.")
        done |= ready
        remaining = {key: deps for key, deps in remaining.items() if key not in ready}
    return spec


async def execute(args: list[str], cwd: str, prefix: Path, seconds: int, record: dict, save: Any) -> int:
    """Own a process group until exit, timeout, or cancellation, including descendants."""
    record.update(args=args, started_at=now())
    with prefix.with_suffix(".stdout").open("wb") as out, prefix.with_suffix(".stderr").open("wb") as err:
        process = await asyncio.create_subprocess_exec(
            *args,
            cwd=cwd,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=out,
            stderr=err,
            start_new_session=True,
        )
        record["pid"] = process.pid
        try:
            save()
            code = await asyncio.wait_for(process.wait(), seconds)
            record["exit_code"] = code
            return code
        finally:
            # Also clean children left behind by an exited group leader; never signal a saved PID on resume.
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGTERM)
            try:
                await asyncio.wait_for(process.wait(), 2)
            finally:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
                await process.wait()
                record["ended_at"] = now()
                save()


async def batch(spec: dict[str, Any], root: Path) -> dict[str, Any]:
    ledger: dict[str, Any] = {"started_at": now(), "tasks": {t["id"]: {"state": "queued"} for t in spec["tasks"]}}
    rows: dict[str, dict[str, Any]] = ledger["tasks"]

    def save() -> None:
        write_json(root / "ledger.json", ledger)

    async def worker(task: dict[str, Any]) -> None:
        row = rows[task["id"]]
        folder = root / task["id"]
        folder.mkdir()
        row.update(state="running", checks=[], details=str(folder))
        prompt = task["prompt"] + (
            "\nComplete only this task; do not delegate further. Preserve unrelated work. "
            "Do not change authentication, permissions or billing. Return at most 120 words: "
            "outcome, changed files, checks and blockers. Follow workspace instructions."
        )
        (folder / "brief.md").write_text(prompt)
        args = [prompt if arg == "{prompt}" else arg for arg in task.get("command", [])]
        if not args:
            args = [
                "agy",
                "-p",
                prompt,
                "--model",
                task["model"],
                "--effort",
                task["effort"],
                "--output-format",
                "json",
                "--disable-slash-commands",
                "--print-timeout",
                f"{spec['timeout']}s",
            ]
            for directory in task["add_dirs"]:
                args.extend(["--add-dir", directory])
            if task.get("conversation_id"):
                args.extend(["--conversation", task["conversation_id"]])
        try:
            row["process"] = {}
            code = await execute(args, task["workspace"], folder / "worker", spec["timeout"], row["process"], save)
            if code:
                raise ValueError("Worker exited nonzero; inspect worker.stderr and worker.stdout.")
            output = folder / "worker.stdout"
            if output.stat().st_size > 8 * 1024 * 1024:
                raise ValueError("Worker result exceeds 8 MiB; inspect the saved output.")
            response = output.read_text()
            if task["result_format"] == "agy-json":
                payload = json.loads(response)
                if not isinstance(payload, dict):
                    raise ValueError("Worker JSON must be an object.")
                row["provider_status"] = payload.get("status")
                row["conversation_id"] = payload.get("conversation_id")
                row["usage"] = payload.get("usage")
                if row["provider_status"] != "SUCCESS":
                    raise ValueError("Provider did not report SUCCESS; inspect worker.stdout.")
                response = payload.get("response")
            if not isinstance(response, str) or not response.strip():
                raise ValueError("Worker response is empty or invalid.")
            row["summary"] = response[:600]
            row["diagnostics_present"] = bool((folder / "worker.stderr").stat().st_size)
            row["state"] = "checking"
            save()
            for index, check in enumerate(task["checks"]):
                record: dict[str, Any] = {}
                row["checks"].append(record)
                if await execute(check, task["workspace"], folder / f"check-{index}", spec["timeout"], record, save):
                    raise ValueError(f"Acceptance check {index} failed; inspect check-{index}.stderr/stdout.")
            row["state"] = "verified" if task["checks"] and not row["diagnostics_present"] else "needs_review"
        except asyncio.CancelledError:
            row["state"] = "canceled"
            raise
        except (OSError, ValueError, TimeoutError) as error:
            row.update(state="failed", error=str(error) if isinstance(error, ValueError) else type(error).__name__)
        finally:
            row["ended_at"] = now()
            save()

    def overlaps(left: dict, right: dict) -> bool:
        return any(
            a == b or a in b.parents or b in a.parents
            for a in map(Path, [left["workspace"], *left["add_dirs"]])
            for b in map(Path, [right["workspace"], *right["add_dirs"]])
        )

    running: dict[asyncio.Task, dict] = {}
    pending = list(spec["tasks"])
    current = asyncio.current_task()
    if current is None:
        raise RuntimeError("Missing batch task")
    loop = asyncio.get_running_loop()

    def stop() -> None:
        if not current.cancelling():
            current.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop)
    save()
    try:
        while pending or running:
            for task in pending[:]:
                dependencies = [rows[key]["state"] for key in task["depends_on"]]
                if any(state in {"failed", "blocked", "canceled", "needs_review"} for state in dependencies):
                    rows[task["id"]].update(state="blocked", error="Prerequisite failed or needs coordinator review.")
                    pending.remove(task)
                elif all(state == "verified" for state in dependencies) and len(running) < spec["concurrency"]:
                    if not any(overlaps(task, active) for active in running.values()):
                        running[asyncio.create_task(worker(task))] = task
                        pending.remove(task)
            save()
            if running:
                finished, _ = await asyncio.wait(running, return_when=asyncio.FIRST_COMPLETED)
                for job in finished:
                    del running[job]
                    job.result()
    except asyncio.CancelledError:
        ledger["canceled"] = True
    finally:
        for job in running:
            job.cancel()
        await asyncio.gather(*running, return_exceptions=True)
        for task in pending:
            rows[task["id"]]["state"] = "canceled"
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.remove_signal_handler(sig)
        ledger["ended_at"] = now()
        save()
    return {
        "run": str(root),
        "tasks": [
            {
                "id": key,
                **{k: v for k, v in row.items() if k in {"state", "summary", "error", "details"}},
                "checks_passed": sum(c.get("exit_code") == 0 for c in row.get("checks", [])),
            }
            for key, row in rows.items()
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Authorized batch JSON; see references/tracking.md")
    parser.add_argument("--state-dir", type=Path, default=Path.home() / ".local/state/deleguate-tasks")
    options = parser.parse_args()
    os.umask(0o077)
    try:
        spec = validate(json.loads(options.manifest.read_text()))
        options.state_dir.mkdir(parents=True, exist_ok=True)
        root = Path(tempfile.mkdtemp(prefix="batch-", dir=options.state_dir))
        write_json(root / "manifest.json", spec)
        result = asyncio.run(batch(spec, root))
        write_json(root / "result.json", result)
        sys.stdout.write(json.dumps(result) + "\n")
        return 0 if all(t["state"] == "verified" for t in result["tasks"]) else 1
    except (OSError, ValueError) as error:
        sys.stderr.write(
            json.dumps({"error": str(error) if isinstance(error, ValueError) else type(error).__name__}) + "\n"
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
