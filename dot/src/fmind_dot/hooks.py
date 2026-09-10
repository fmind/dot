"""Host payload validation and bounded failure evidence."""

import hashlib
import json
import os
import stat
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any

from fmind_dot.archive.ingest import _bounded_failure
from fmind_dot.archive.store import (
    is_valid_session_id,
)
from fmind_dot.errors import DotError
from fmind_dot.private_files import (
    _open_or_create_directory_at,
    _open_verified_directory,
    _publish_owner_only_at,
    _safe_agent_fs_available,
)
from fmind_dot.state import State


def decode_copilot_session_end(stream: IO[str] | None) -> dict[str, Any]:
    if stream is None:
        raise DotError("missing Copilot sessionEnd payload")
    content = stream.read()
    try:
        value = json.loads(content)
    except json.JSONDecodeError as error:
        raise DotError(f"invalid Copilot sessionEnd payload: {error}") from error
    expected = {"sessionId", "cwd", "reason", "timestamp"}
    if not isinstance(value, dict) or set(value) != expected:
        raise DotError("invalid Copilot sessionEnd payload: expected documented fields")
    if not isinstance(value["sessionId"], str) or not is_valid_session_id(value["sessionId"]):
        raise DotError(f"invalid Copilot sessionEnd sessionId: {value['sessionId']!r}")
    if not isinstance(value["cwd"], str) or not value["cwd"]:
        raise DotError("invalid Copilot sessionEnd payload: missing cwd")
    if isinstance(value["timestamp"], bool) or not isinstance(value["timestamp"], int) or value["timestamp"] <= 0:
        raise DotError("invalid Copilot sessionEnd payload: timestamp must be Unix milliseconds")
    if not isinstance(value["reason"], str):
        raise DotError("invalid Copilot sessionEnd payload: reason must be a string")
    if value["reason"] not in {"complete", "error", "abort", "timeout", "user_exit"}:
        raise DotError(f"unsupported Copilot sessionEnd reason {value['reason']!r}")
    return value


def _write_hook_failure_record(state: State, agent: str, operation: str, session_id: str, error: BaseException) -> None:
    home = _open_verified_directory(Path.home())
    try:
        agents = _open_or_create_directory_at(home, ".agents", 0o700, enforce_mode=False)
        try:
            failures = _open_or_create_directory_at(agents, "hook-failures", 0o700)
            try:
                root = _open_or_create_directory_at(failures, "v1", 0o700)
            finally:
                os.close(failures)
        finally:
            os.close(agents)
    finally:
        os.close(home)

    try:
        detail = _bounded_failure(error, session_id, state.config.agent.hook_failures.detail_limit)
        session_hash = hashlib.sha256(f"{agent}\0{session_id}\0".encode()).hexdigest()[:12] if session_id else ""
        record: dict[str, Any] = {
            "occurred_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "agent": agent,
            "operation": operation,
        }
        if session_hash:
            record["session_hash"] = session_hash
        record["detail"] = detail
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
        suffix = hashlib.sha256(f"{agent}\0{operation}\0{detail}\0".encode()).hexdigest()[:12]
        records: list[str] = []
        for name in os.listdir(root):  # noqa: PTH208 - the descriptor preserves confinement during races.
            if not name.endswith(".json"):
                continue
            try:
                mode = os.stat(name, dir_fd=root, follow_symlinks=False).st_mode
            except FileNotFoundError:
                continue
            if stat.S_ISREG(mode):
                records.append(name)
        published = f"{stamp}-{suffix}.json"
        content = (json.dumps(record, separators=(",", ":")) + "\n").encode()
        _publish_owner_only_at(root, published, content)
        if published not in records:
            records.append(published)
        records.sort()
        excess = max(0, len(records) - state.config.agent.hook_failures.limit)
        for name in records[:excess]:
            with suppress(FileNotFoundError):
                os.unlink(name, dir_fd=root)
    finally:
        os.close(root)


def _spool_hook_failure(state: State, agent: str, operation: str, session_id: str, error: BaseException) -> None:
    detail_limit = state.config.agent.hook_failures.detail_limit
    if not _safe_agent_fs_available():
        state.stderr.write("agent hook failure spool unavailable: safe filesystem operations are unavailable\n")
        return
    try:
        _write_hook_failure_record(state, agent, operation, session_id, error)
    except Exception as spool_error:
        detail = _bounded_failure(spool_error, session_id, detail_limit)
        state.stderr.write(f"agent hook failure spool unavailable: {detail}\n")
