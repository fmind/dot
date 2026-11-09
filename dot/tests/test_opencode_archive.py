"""OpenCode stores are accepted only while they hold no session."""

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from fmind_dot.archive.parsers import AGENT_ADAPTERS, parse_opencode_session


@pytest.mark.parametrize(
    ("create", "insert", "refusal"),
    [
        pytest.param(
            "CREATE TABLE session_v2 (id TEXT, directory TEXT)",
            "INSERT INTO session_v2 VALUES ('ses_new', '/work/project')",
            r"OpenCode 2\.x sessions \(session_v2\) are not supported",
            id="2.x",
        ),
        pytest.param(
            "CREATE TABLE session (id TEXT, directory TEXT)",
            "INSERT INTO session VALUES ('ses_old', '/work/project')",
            r"OpenCode 1\.x sessions \(session\) are not supported",
            id="1.x",
        ),
    ],
)
def test_opencode_store_is_empty_until_it_holds_sessions(
    tmp_path: Path, create: str, insert: str, refusal: str
) -> None:
    store = tmp_path / "opencode.db"
    with closing(sqlite3.connect(store)) as db, db:
        db.execute(create)
    enumerate_sessions = AGENT_ADAPTERS["opencode"].enumerate
    assert enumerate_sessions(store) == []
    with closing(sqlite3.connect(store)) as db, db:
        db.execute(insert)
    with pytest.raises(ValueError, match=refusal):
        enumerate_sessions(store)


def test_opencode_sessions_are_never_parsed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="OpenCode sessions are not supported"):
        parse_opencode_session(tmp_path / "opencode.db", "ses_test")
