from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from fmind_dot.config import Config, config_file_path, expand_path, load_config


def test_python_first_defaults_replace_retired_stacks() -> None:
    config = Config()

    assert config.schema_version == 3
    assert set(Config.model_fields) == {"schema_version", "agent", "doctor", "completions", "pull"}
    assert config.agent.doctor.scan_limit == 16384
    assert config.pull.timeout_seconds == 120.0


def test_verify_inventory_covers_managed_harnesses_and_core_workflows() -> None:
    config = Config()
    expected = {*config.agent.sources, "opencode", "fkf", "marimo"}
    assert expected <= set(config.doctor.tools)


def test_load_config_is_strict_and_rejects_trailing_documents(tmp_path: Path) -> None:
    unknown = tmp_path / "unknown.yaml"
    unknown.write_text("unknown: true\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_config(unknown)

    trailing = tmp_path / "trailing.yaml"
    trailing.write_text("ai:\n  binary: claude\n---\nai:\n  binary: codex\n", encoding="utf-8")
    with pytest.raises(ValueError, match="exactly one YAML document"):
        load_config(trailing)


@pytest.mark.parametrize(
    ("document", "field"),
    [
        ("pull:\n  concurrency: VALUE\n", "concurrency"),
        ("doctor:\n  probe_concurrency: VALUE\n", "probe_concurrency"),
        ("agent:\n  doctor:\n    scan_limit: VALUE\n", "scan_limit"),
        ("doctor:\n  secrets:\n    - path: ~/.config/key\n      required_perms: VALUE\n", "required_perms"),
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
        "doctor:\n  tools: [python]\ncompletions:\n  custom_commands:\n    custom:\n      args: [completion, fish]\n",
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.doctor.tools == ["python"]
    assert "uv" in config.completions.custom_commands
    assert config.completions.custom_commands["custom"].args == ["completion", "fish"]


@pytest.mark.parametrize(
    "document",
    [
        "context:\n  max_bytes: 1000\n",
        "release:\n  workflow: cd.yml\n",
        "completions:\n  concurrency: 4\n",
    ],
)
def test_removed_configuration_fields_are_rejected(tmp_path: Path, document: str) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text(document, encoding="utf-8")

    with pytest.raises(ValidationError):
        load_config(path)


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


@pytest.mark.parametrize("value", ["true", '"30s"', '"30"', "0", "-1", ".nan", ".inf"])
def test_timeouts_reject_invalid_or_ambiguous_seconds(tmp_path: Path, value: str) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text(f"pull:\n  timeout_seconds: {value}\n")
    with pytest.raises(ValidationError, match="timeout_seconds"):
        load_config(path)


@pytest.mark.parametrize("value", ["30", "0.5"])
def test_timeouts_accept_positive_numeric_seconds(tmp_path: Path, value: str) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text(f"pull:\n  timeout_seconds: {value}\n")
    assert load_config(path).pull.timeout_seconds == float(value)
