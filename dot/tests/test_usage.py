from __future__ import annotations

import json
import stat
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from fmind_dot.cli import app, main
from fmind_dot.usage import (
    UsageRecord,
    UsageStats,
    aggregate_usage,
    list_usage_records,
    load_usage_records,
    parse_flexible_time,
    sanitize_filename,
    show_usage_record,
    usage_root,
    write_usage_record,
    write_usage_stats,
)


def _write_raw_usage_record(root: Path, **overrides: Any) -> Path:
    value: dict[str, Any] = {
        "timestamp": "2026-09-06T10:00:00Z",
        "harness": "codex",
        "agent": "codex",
        "session_id": "broken",
        "model": "gpt",
        "cwd": "project",
        "input_tokens": 1,
        "output_tokens": 2,
        "cached_tokens": 3,
        "cache_write_tokens": 4,
        "reasoning_tokens": 5,
        "total_tokens": 15,
        "cost_usd": 0.25,
        "turn_count": 1,
    }
    value.update(overrides)
    path = root / "codex" / "broken.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    return path


def test_usage_records_publish_atomically_and_aggregate(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    records = [
        UsageRecord(harness="codex", session_id="same", model="gpt", input_tokens=index, output_tokens=2)
        for index in range(8)
    ]
    with ThreadPoolExecutor(max_workers=4) as executor:
        paths = list(executor.map(write_usage_record, records))
    assert len(set(paths)) == 1
    assert stat.S_IMODE(paths[0].stat().st_mode) == 0o600
    value = json.loads(paths[0].read_text(encoding="utf-8"))
    assert value["agent"] == "codex"
    loaded = load_usage_records()
    assert len(loaded) == 1
    rows = aggregate_usage(loaded, by_model=True)
    assert len(rows) == 1
    assert rows[0].sessions == 1


def test_usage_record_finalizes_defaults_and_computed_total() -> None:
    record = UsageRecord(
        harness="codex",
        session_id="session",
        input_tokens=1,
        output_tokens=2,
        cached_tokens=3,
        cache_write_tokens=4,
    )

    assert record.finalize() is record
    assert record.agent == "codex"
    assert datetime.fromisoformat(record.timestamp).tzinfo is not None
    assert record.total_tokens == 10


def test_usage_record_serializes_every_explicit_field() -> None:
    record = UsageRecord(
        timestamp="2026-09-06T10:00:00Z",
        harness="codex",
        agent="worker",
        session_id="session",
        model="gpt",
        cwd="/repo",
        input_tokens=1,
        output_tokens=2,
        cached_tokens=3,
        cache_write_tokens=4,
        reasoning_tokens=5,
        total_tokens=20,
        cost_usd=0.25,
        turn_count=2,
    )

    assert record.finalize().to_dict() == {
        "timestamp": "2026-09-06T10:00:00Z",
        "harness": "codex",
        "agent": "worker",
        "session_id": "session",
        "model": "gpt",
        "cwd": "/repo",
        "input_tokens": 1,
        "output_tokens": 2,
        "cached_tokens": 3,
        "cache_write_tokens": 4,
        "reasoning_tokens": 5,
        "total_tokens": 20,
        "cost_usd": 0.25,
        "turn_count": 2,
    }


def test_usage_rejects_missing_identity(tmp_path) -> None:
    with pytest.raises(ValueError, match="missing harness"):
        write_usage_record(UsageRecord(session_id="x"), root=tmp_path)
    with pytest.raises(ValueError, match="missing session_id"):
        write_usage_record(UsageRecord(harness="codex"), root=tmp_path)


@pytest.mark.parametrize("harness", ["../escape", "/escape", ".", "claude/session"])
def test_usage_rejects_unsafe_harness_path_components(tmp_path: Path, harness: str) -> None:
    record = UsageRecord(harness=harness, session_id="session")

    with pytest.raises(ValueError, match="invalid harness"):
        write_usage_record(record, root=tmp_path)
    with pytest.raises(ValueError, match="invalid harness"):
        show_usage_record(harness, "session", root=tmp_path)


def test_usage_rejects_linked_harness_storage(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "usages"
    root.mkdir()
    (root / "codex").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symbolic link"):
        write_usage_record(UsageRecord(harness="codex", session_id="session"), root=root)
    with pytest.raises(ValueError, match="symbolic link"):
        show_usage_record("codex", "session", root=root)

    assert list(outside.iterdir()) == []


def test_load_usage_records_rejects_linked_root(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    _write_raw_usage_record(outside)
    root = tmp_path / "usages"
    root.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="failed to parse usage record") as raised:
        load_usage_records(root=root)

    assert str(root) in str(raised.value)
    assert "symbolic link" in str(raised.value)


def test_usage_storage_rejects_non_directory_paths(tmp_path: Path) -> None:
    root = tmp_path / "usages"
    root.write_text("occupied", encoding="utf-8")
    record = UsageRecord(harness="codex", session_id="session")

    with pytest.raises(ValueError, match="usage root must be a directory"):
        write_usage_record(record, root=root)
    with pytest.raises(ValueError, match="usage root must be a directory"):
        show_usage_record("codex", "session", root=root)

    root.unlink()
    root.mkdir()
    (root / "codex").write_text("occupied", encoding="utf-8")
    with pytest.raises(ValueError, match="usage harness path must be a directory"):
        show_usage_record("codex", "session", root=root)


def test_show_usage_record_rejects_link_and_reports_missing_inputs(tmp_path: Path) -> None:
    root = tmp_path / "usages"
    directory = root / "codex"
    directory.mkdir(parents=True)
    outside = tmp_path / "outside.json"
    outside.write_text('{"secret": true}\n', encoding="utf-8")
    (directory / "session.json").symlink_to(outside)

    with pytest.raises(ValueError, match="usage record must not be a symbolic link"):
        show_usage_record("codex", "session", root=root)
    with pytest.raises(ValueError, match="usage: dot agent usage show"):
        show_usage_record("", "session", root=root)
    with pytest.raises(ValueError, match="usage: dot agent usage show"):
        show_usage_record("codex", "", root=root)
    with pytest.raises(ValueError, match="usage record not found"):
        show_usage_record("codex", "missing", root=root)


def test_usage_session_ids_are_confined_to_the_harness_directory(tmp_path: Path) -> None:
    record = UsageRecord(harness="codex", session_id="../outside", input_tokens=1)

    path = write_usage_record(record, root=tmp_path)

    assert path == tmp_path / "codex" / "___outside.json"
    assert show_usage_record("codex", "../outside", root=tmp_path) == path.read_bytes()
    assert sanitize_filename("safe-Name_1/é") == "safe-Name_1__"


def test_usage_record_from_dict_rejects_empty_object() -> None:
    with pytest.raises(ValueError, match="missing timestamp in usage record"):
        UsageRecord.from_dict({})


@pytest.mark.parametrize("field", ["timestamp", "harness", "agent", "session_id"])
def test_usage_record_from_dict_requires_complete_identity(field: str) -> None:
    value = {
        "timestamp": "2026-09-06T10:00:00Z",
        "harness": "codex",
        "agent": "codex",
        "session_id": "valid",
    }
    del value[field]

    with pytest.raises(ValueError, match=f"missing {field} in usage record"):
        UsageRecord.from_dict(value)


@pytest.mark.parametrize(
    ("field", "value"),
    [("input_tokens", -1), ("cost_usd", -0.01), ("cost_usd", float("inf"))],
    ids=["negative-tokens", "negative-cost", "infinite-cost"],
)
def test_usage_rejects_invalid_metrics_before_serialization(
    tmp_path: Path,
    field: str,
    value: int | float,
) -> None:
    record = UsageRecord(
        timestamp="2026-09-06T10:00:00Z",
        harness="codex",
        agent="codex",
        session_id="invalid",
    )
    setattr(record, field, value)

    with pytest.raises(ValueError, match=field):
        record.to_dict()
    with pytest.raises(ValueError, match=field):
        write_usage_record(record, root=tmp_path)

    assert not list(tmp_path.rglob("*.json"))


def test_usage_rejects_malformed_timestamp_at_every_boundary(tmp_path: Path) -> None:
    record = UsageRecord(
        timestamp="not-a-time",
        harness="codex",
        agent="codex",
        session_id="invalid",
    )

    with pytest.raises(ValueError, match="timestamp"):
        record.finalize()
    with pytest.raises(ValueError, match="timestamp"):
        record.to_dict()
    with pytest.raises(ValueError, match="timestamp"):
        write_usage_record(record, root=tmp_path)
    with pytest.raises(ValueError, match="timestamp"):
        aggregate_usage([record], since=datetime(2026, 1, 1, tzinfo=UTC))

    assert not list(tmp_path.rglob("*.json"))

    path = _write_raw_usage_record(tmp_path, timestamp="not-a-time")
    with pytest.raises(ValueError, match="failed to parse usage record") as raised:
        load_usage_records(root=tmp_path)

    assert str(path) in str(raised.value)
    assert "timestamp" in str(raised.value)


@pytest.mark.parametrize(
    "timestamp",
    ["NaN", "Infinity", "10000-01-01T00:00:00Z", "0001-01-01T00:00:00+23:59"],
    ids=["nan", "infinity", "unparseable-year", "utc-underflow"],
)
def test_usage_rejects_non_finite_and_out_of_range_timestamps(timestamp: str) -> None:
    record = UsageRecord(
        timestamp=timestamp,
        harness="codex",
        agent="codex",
        session_id="invalid",
    )

    with pytest.raises(ValueError, match="timestamp"):
        record.to_dict()
    with pytest.raises(ValueError, match="timestamp"):
        aggregate_usage([record])


@pytest.mark.parametrize(
    "timestamp",
    ["2026-09-06T10:00:00.123456Z", "2026-09-06T12:00:00+02:00", "2026-09-06T10:00:00"],
    ids=["utc-z", "explicit-offset", "implicit-utc"],
)
def test_usage_preserves_accepted_iso_timestamp_formats(timestamp: str) -> None:
    record = UsageRecord(
        timestamp=timestamp,
        harness="codex",
        agent="codex",
        session_id="valid",
    )

    assert record.to_dict()["timestamp"] == timestamp
    assert aggregate_usage([record], since=datetime(2026, 9, 6, 9, 59, tzinfo=UTC))[0].sessions == 1


def test_aggregate_usage_projects_unknown_model_when_grouping_by_model() -> None:
    record = UsageRecord(
        timestamp="2026-09-06T10:00:00Z",
        harness="codex",
        agent="codex",
        session_id="session",
    )

    row = aggregate_usage([record], by_model=True)[0]

    assert row.model == "unknown"
    assert row.to_dict()["model"] == "unknown"


def test_aggregate_usage_filters_and_sums_every_metric() -> None:
    records = [
        UsageRecord(
            timestamp="2026-09-06T09:00:00Z",
            harness="codex",
            agent="codex",
            session_id="early",
            model="gpt",
            input_tokens=1,
            total_tokens=1,
        ),
        UsageRecord(
            timestamp="2026-09-06T10:00:00Z",
            harness="codex",
            agent="codex",
            session_id="included",
            model="gpt-mini",
            input_tokens=1,
            output_tokens=2,
            cached_tokens=3,
            cache_write_tokens=4,
            reasoning_tokens=5,
            total_tokens=15,
            cost_usd=0.25,
            turn_count=2,
        ),
        UsageRecord(
            timestamp="2026-09-06T11:00:00Z",
            harness="codex",
            agent="codex",
            session_id="late",
            model="gpt",
            output_tokens=10,
            total_tokens=10,
        ),
        UsageRecord(
            timestamp="2026-09-06T10:15:00Z",
            harness="claude",
            agent="worker",
            session_id="other",
            model="sonnet",
            total_tokens=7,
        ),
    ]

    filtered = aggregate_usage(
        records,
        harness="codex",
        since=datetime(2026, 9, 6, 9, 30, tzinfo=UTC),
        until=datetime(2026, 9, 6, 10, 30, tzinfo=UTC),
        by_model=True,
    )

    assert [row.to_dict() for row in filtered] == [
        {
            "harness": "codex",
            "model": "gpt-mini",
            "input_tokens": 1,
            "output_tokens": 2,
            "cached_tokens": 3,
            "cache_write_tokens": 4,
            "reasoning_tokens": 5,
            "total_tokens": 15,
            "cost_usd": 0.25,
            "sessions": 1,
            "turns": 2,
        }
    ]

    combined = aggregate_usage(records)
    assert [(row.harness, row.sessions, row.total_tokens) for row in combined] == [
        ("claude", 1, 7),
        ("codex", 3, 26),
    ]
    assert aggregate_usage(records, harness="worker")[0].harness == "claude"


def test_list_usage_records_filters_sorts_and_applies_limit() -> None:
    records = [
        UsageRecord(timestamp="2026-09-06T09:00:00Z", harness="codex", agent="codex", session_id="old"),
        UsageRecord(timestamp="2026-09-06T11:00:00Z", harness="codex", agent="worker", session_id="new"),
        UsageRecord(timestamp="2026-09-06T10:00:00Z", harness="claude", agent="claude", session_id="other"),
    ]

    assert [record.session_id for record in list_usage_records(records, harness="codex", limit=1)] == ["new"]
    assert [record.session_id for record in list_usage_records(records, harness="worker", limit=0)] == ["new"]
    assert [record.session_id for record in list_usage_records(records, limit=-1)] == ["new", "other", "old"]


def test_write_usage_stats_renders_json_empty_and_text_contracts() -> None:
    rows = [
        UsageStats(
            harness="claude",
            model="sonnet",
            input_tokens=1000,
            output_tokens=2,
            cached_tokens=3,
            cache_write_tokens=4,
            reasoning_tokens=5,
            total_tokens=1014,
            cost_usd=0.5,
            sessions=1,
            turns=2,
        ),
        UsageStats(
            harness="codex",
            model="gpt",
            input_tokens=1,
            output_tokens=2,
            reasoning_tokens=1,
            total_tokens=4,
            cost_usd=0.125,
            sessions=2,
            turns=3,
        ),
    ]

    output = StringIO()
    write_usage_stats(output, rows, as_json=True, by_model=True)
    document = json.loads(output.getvalue())
    assert [row["model"] for row in document] == ["sonnet", "gpt"]
    assert document[0]["cache_write_tokens"] == 4

    output = StringIO()
    write_usage_stats(output, [], as_json=False, by_model=False)
    assert output.getvalue() == (
        "No usage records found in ~/.agents/usages. Run 'dot agent usage sync' to backfill existing sessions.\n"
    )

    output = StringIO()
    write_usage_stats(output, rows, as_json=False, by_model=True)
    assert output.getvalue().splitlines() == [
        "HARNESS\tMODEL\tSESSIONS\tTURNS\tINPUT TOKENS\tOUTPUT TOKENS\tCACHED TOKENS\tREASONING\tTOTAL TOKENS\tCOST (USD)",
        "claude\tsonnet\t1\t2\t1,000\t2\t3\t5\t1,014\t$0.5000",
        "codex\tgpt\t2\t3\t1\t2\t0\t1\t4\t$0.1250",
        "TOTAL\t-\t3\t5\t1,001\t4\t3\t6\t1,018\t$0.6250",
    ]

    output = StringIO()
    write_usage_stats(output, rows[:1], as_json=False, by_model=False)
    assert output.getvalue().splitlines()[0].startswith("HARNESS\tSESSIONS")
    assert output.getvalue().splitlines()[-1].startswith("TOTAL\t1\t2")


def test_usage_cli_lists_filters_aggregates_and_shows_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    for record in (
        UsageRecord(
            timestamp="2026-09-06T09:00:00Z",
            harness="codex",
            session_id="old",
            model="gpt",
            total_tokens=2,
        ),
        UsageRecord(
            timestamp="2026-09-06T10:00:00Z",
            harness="codex",
            session_id="new",
            model="gpt-mini",
            total_tokens=3,
            cost_usd=0.25,
        ),
    ):
        write_usage_record(record)

    runner = CliRunner()
    listed = runner.invoke(app, ["agent", "usage", "list", "--harness", "codex", "--limit", "1", "--json"])
    stats = runner.invoke(
        app,
        [
            "agent",
            "usage",
            "stats",
            "--since",
            "2026-09-06T09:30:00Z",
            "--until",
            "2026-09-06T10:30:00Z",
            "--by-model",
            "--json",
        ],
    )
    shown = runner.invoke(app, ["agent", "usage", "show", "codex", "new"])

    assert listed.exit_code == 0
    assert [record["session_id"] for record in json.loads(listed.stdout)] == ["new"]
    assert stats.exit_code == 0
    assert [(row["model"], row["total_tokens"]) for row in json.loads(stats.stdout)] == [("gpt-mini", 3)]
    assert shown.exit_code == 0
    assert json.loads(shown.stdout)["session_id"] == "new"


@pytest.mark.parametrize("field", ["timestamp", "harness", "agent", "session_id", "model", "cwd"])
def test_load_usage_records_rejects_non_string_fields(tmp_path: Path, field: str) -> None:
    path = _write_raw_usage_record(tmp_path, **{field: 1})

    with pytest.raises(ValueError, match="failed to parse usage record") as raised:
        load_usage_records(root=tmp_path)

    assert str(path) in str(raised.value)
    assert field in str(raised.value)


@pytest.mark.parametrize(
    "cost",
    ["0.25", float("nan"), -0.25, True, 10**400],
    ids=["string", "nan", "negative", "boolean", "float-overflow"],
)
def test_load_usage_records_rejects_invalid_cost(tmp_path: Path, cost: Any) -> None:
    path = _write_raw_usage_record(tmp_path, cost_usd=cost)

    with pytest.raises(ValueError, match="failed to parse usage record") as raised:
        load_usage_records(root=tmp_path)

    assert str(path) in str(raised.value)
    assert "cost_usd" in str(raised.value)


def test_load_usage_records_preserves_integer_cost_compatibility(tmp_path: Path) -> None:
    _write_raw_usage_record(tmp_path, cost_usd=1)

    records = load_usage_records(root=tmp_path)

    assert records[0].cost_usd == 1.0


@pytest.mark.parametrize("content", ["[]\n", "{broken\n"], ids=["non-object", "malformed-json"])
def test_load_usage_records_contextualizes_invalid_json(tmp_path: Path, content: str) -> None:
    path = tmp_path / "codex" / "broken.json"
    path.parent.mkdir(parents=True)
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="failed to parse usage record") as raised:
        load_usage_records(root=tmp_path)

    assert str(path) in str(raised.value)


def test_load_usage_records_tolerates_a_file_disappearing_during_scan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _write_raw_usage_record(tmp_path)
    original_read_text = Path.read_text

    def disappear(candidate: Path, *args: Any, **kwargs: Any) -> str:
        if candidate == path:
            candidate.unlink()
            raise FileNotFoundError(candidate)
        return original_read_text(candidate, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", disappear)

    assert load_usage_records(root=tmp_path) == []


def test_usage_root_follows_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    assert usage_root() == tmp_path / ".agents" / "usages"


def test_parse_flexible_time_supports_durations_days_and_iso_values() -> None:
    now = datetime(2026, 9, 6, 12, 0, tzinfo=UTC)

    assert parse_flexible_time(" 1h30m15s ", now=now) == now - timedelta(hours=1, minutes=30, seconds=15)
    assert parse_flexible_time("7d", now=now) == now - timedelta(days=7)
    assert parse_flexible_time("2026-09-01", now=now) == datetime(2026, 9, 1, tzinfo=UTC)
    assert parse_flexible_time("2026-09-06T14:00:00+02:00", now=now) == now


@pytest.mark.parametrize("value", ["", "0d", "1h-no"])
def test_parse_flexible_time_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError, match="use a duration"):
        parse_flexible_time(value, now=datetime(2026, 9, 6, tzinfo=UTC))


@pytest.mark.parametrize("command", ["list", "stats"])
def test_usage_commands_report_invalid_records_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    command: str,
) -> None:
    root = tmp_path / ".agents" / "usages"
    path = _write_raw_usage_record(root, model=42)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(sys, "argv", ["dot", "agent", "usage", command])

    with pytest.raises(SystemExit) as raised:
        main()

    captured = capsys.readouterr()
    assert raised.value.code == 1
    assert captured.out == ""
    assert f"dot: failed to parse usage record {path}" in captured.err
    assert "Traceback" not in captured.err
