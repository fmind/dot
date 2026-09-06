from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from fmind_dot.config import Config, config_file_path, duration_seconds, expand_path, load_config
from fmind_dot.maintenance import _session_source


def test_python_first_defaults_replace_retired_stacks() -> None:
    config = Config()

    assert "hermes" not in config.agent.sources
    assert "hermes" not in {store.source for store in config.prune.agents.sessions}
    assert not hasattr(config.prune, "go")
    assert not hasattr(config.prune, "node")
    assert "hermes" not in config.verify.tools
    assert "go" not in config.verify.tools


def test_load_config_is_strict_and_rejects_trailing_documents(tmp_path: Path) -> None:
    unknown = tmp_path / "unknown.yaml"
    unknown.write_text("unknown: true\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_config(unknown)

    trailing = tmp_path / "trailing.yaml"
    trailing.write_text("ai:\n  binary: claude\n---\nai:\n  binary: codex\n", encoding="utf-8")
    with pytest.raises(ValueError, match="exactly one YAML document"):
        load_config(trailing)


@pytest.mark.parametrize("value", ["false", '"0"'])
def test_retention_rejects_coerced_boolean_and_string_values(tmp_path: Path, value: str) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text(
        f"prune:\n  agents:\n    sessions:\n      - path: ~/.agents/sessions\n        keep_days: {value}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="keep_days"):
        load_config(path)


@pytest.mark.parametrize(
    ("document", "field"),
    [
        ("completions:\n  concurrency: VALUE\n", "concurrency"),
        ("pull:\n  concurrency: VALUE\n", "concurrency"),
        ("verify:\n  probe_concurrency: VALUE\n", "probe_concurrency"),
        ("context:\n  max_bytes: VALUE\n", "max_bytes"),
        ("commit:\n  max_diff_size: VALUE\n", "max_diff_size"),
        ("agent:\n  doctor:\n    scan_limit: VALUE\n", "scan_limit"),
        ("verify:\n  secrets:\n    - path: ~/.config/key\n      required_perms: VALUE\n", "required_perms"),
    ],
)
@pytest.mark.parametrize("value", ["false", '"8"'])
def test_operational_integer_scalars_reject_yaml_coercion(
    tmp_path: Path, document: str, field: str, value: str
) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text(document.replace("VALUE", value), encoding="utf-8")

    with pytest.raises(ValidationError, match=field):
        load_config(path)


def test_config_overlay_replaces_lists_and_merges_maps(tmp_path: Path) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text(
        "verify:\n  tools: [python]\ncompletions:\n  custom_commands:\n    custom:\n      args: [completion, fish]\n",
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.verify.tools == ["python"]
    assert "uv" in config.completions.custom_commands
    assert config.completions.custom_commands["custom"].args == ["completion", "fish"]


def test_legacy_path_only_session_stores_load_and_preserve_source_inference(tmp_path: Path) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text(
        "prune:\n"
        "  agents:\n"
        "    sessions:\n"
        "      - path: ~/.claude/projects\n"
        "      - path: ~/custom-sessions\n"
        "        keep_days: 90\n",
        encoding="utf-8",
    )

    config = load_config(path)
    known, custom = config.prune.agents.sessions

    assert known.source == ""
    assert known.keep_days == 30
    assert _session_source(known) == "claude"
    assert custom.source == ""
    assert custom.keep_days == 90
    assert _session_source(custom) == ""


def test_load_config_wraps_yaml_and_decode_failures_with_path_context(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.yaml"
    malformed.write_text("prune: [\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"failed to parse config file at .*malformed\.yaml"):
        load_config(malformed)

    undecodable = tmp_path / "undecodable.yaml"
    undecodable.write_bytes(b"\xff")
    with pytest.raises(ValueError, match=r"failed to read config file at .*undecodable\.yaml"):
        load_config(undecodable)

    directory = tmp_path / "directory.yaml"
    directory.mkdir()
    with pytest.raises(ValueError, match=r"failed to read config file at .*directory\.yaml"):
        load_config(directory)


def test_path_resolution_expands_only_current_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    assert expand_path("~") == tmp_path
    assert expand_path("~/project") == tmp_path / "project"
    assert expand_path("~someone/project") == Path("~someone/project")
    assert config_file_path(None) == (tmp_path / ".config/dot.yaml", True)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1ms", 0.001),
        ("1.5s", 1.5),
        (".5m", 30.0),
        ("1h30m250ms", 5_400.25),
    ],
)
def test_duration_parser_preserves_go_compatible_units_and_fractions(value: str, expected: float) -> None:
    assert duration_seconds(value) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("", "duration must be a string"),
        ("1d", "invalid duration"),
        ("0s", "must be positive"),
        ("9999999999h", "exceeds the Go duration range"),
    ],
)
def test_duration_parser_rejects_invalid_nonpositive_and_overflow_values(value: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        duration_seconds(value)


@pytest.mark.parametrize("content", ["", "---\n"])
def test_empty_config_documents_use_defaults(tmp_path: Path, content: str) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text(content, encoding="utf-8")

    assert load_config(path) == Config()


def test_config_document_requires_a_mapping(tmp_path: Path) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text("- invalid\n", encoding="utf-8")

    with pytest.raises(ValueError, match="must contain a YAML mapping"):
        load_config(path)
