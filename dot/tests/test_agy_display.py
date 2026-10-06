"""Check terminal rendering and managed settings without a provider or real home."""

import json
import os
import runpy
import shlex
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/agy/scripts/display.py"
display = runpy.run_path(str(SCRIPT))
render = display["render"]


def state() -> dict[str, object]:
    return {
        "cwd": "/private/owner/dot",
        "vcs": {"branch": "main", "dirty": True},
        "agent_state": "working",
        "context_window": {"used_percentage": 24.3, "context_window_size": 1048576},
        "task_count": 2,
        "quota": {
            "weekly": {"remaining_fraction": 0.75, "reset_in_seconds": 60},
            "other": {"remaining_fraction": 0.6, "reset_in_seconds": 7500},
        },
        "model": {"display_name": "Flash High"},
        "terminal_width": 140,
        "email": "private@example.test",
        "conversation_id": "private-conversation",
        "transcript_path": "/private/transcript.jsonl",
        "vim": {"mode": "INSERT"},
    }


def test_state_display_and_title_omit_sensitive_fields() -> None:
    payload = state()
    assert render(payload, "statusline") == (
        "\uf07b dot \ue0b1 \ue0a0 main* \ue0b1 \uf110 working \ue0b1 \uf2db Flash High"
        " \ue0b1 \uf0e4 context 24% · 255k/1M \ue0b1 \uf0ae 2 tasks"
        " \ue0b1 \uf242 quota min 60% left ↻ 2h05m \ue0b1 \ue62b INSERT"
    )
    assert render(payload, "title") == "dot* — working · 2 tasks"
    payload.update(agent_state="idle")
    assert "background" in render(payload, "title")
    payload.update(tool_confirmation_pending=True)
    assert "needs input" in render(payload, "title")


@pytest.mark.parametrize("width", [1, 2, 20, 40])
def test_narrow_rendering_fits_terminal_columns(width: int) -> None:
    payload = state()
    payload.update(terminal_width=width, cwd="/some/界界界")
    text = render(payload, "statusline")
    measured = sum(2 if c == "界" else 1 for c in text)
    assert measured <= max(1, width - 1)


@pytest.mark.parametrize(
    ("text", "width", "expected"),
    [
        ("feature/very-long-branch-name", 20, "feature/very-long-b…"),
        ("abcdefghij", 5, "abcd…"),
        ("日本語テキスト", 5, "日本…"),
        ("abc", 1, "…"),
        ("abc", 0, ""),
        ("fits", 4, "fits"),
    ],
)
def test_clip_keeps_a_prefix_within_columns(text: str, width: int, expected: str) -> None:
    assert display["clip"](text, width) == expected


def test_untrusted_strings_cannot_emit_terminal_controls() -> None:
    payload = state()
    payload.update(
        cwd="/" + "long/" * 100 + "dot",
        vcs={"branch": "\x1b]52;c;private\x07main\n\x1b[31m", "dirty": True},
        model={"display_name": "Flash\x1b[0m\u202e\x07"},
    )
    text = render(payload, "statusline")
    assert text.startswith("\uf07b dot \ue0b1 \ue0a0 main*")
    assert "private" not in text
    # Nerd Font icons are private-use characters; everything else must stay printable.
    assert all(c.isprintable() or unicodedata.category(c) == "Co" for c in text)


@pytest.mark.parametrize("bad", [None, True, "20", -1, float("nan"), float("inf"), 10**1000])
def test_invalid_metrics_are_omitted(bad: object) -> None:
    payload = {"context_window": {"used_percentage": bad}, "quota": {"weekly": {"remaining_fraction": bad}}}
    assert render(payload, "statusline") == "\uf07b agy \ue0b1 \uf110 starting"


@pytest.mark.parametrize(
    "raw",
    ["{", "[]", "null", '{"email":"private@example.test"}', " " * 131073],
    ids=["malformed", "array", "null", "private", "oversized"],
)
def test_invalid_or_empty_input_has_quiet_fallback(raw: str) -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "title"], input=raw, capture_output=True, text=True, check=False, timeout=10
    )
    assert result.returncode == 0
    assert result.stdout == "agy — starting\n"
    assert result.stderr == ""


def test_managed_config_preserves_host_preferences_and_is_repeatable(tmp_path: Path) -> None:
    source = tmp_path / "source"
    templates = source / ".chezmoitemplates"
    templates.mkdir(parents=True)
    shutil.copyfile(ROOT / ".chezmoitemplates/json-merge.tmpl", templates / "json-merge.tmpl")
    template = tmp_path / "settings.tmpl"
    template.write_text(
        (ROOT / "dot_gemini/antigravity-cli/modify_private_settings.json").read_text().split("\n", 1)[1]
    )
    config = tmp_path / "chezmoi.toml"
    config.write_text("")
    command = [
        "chezmoi",
        "--source",
        str(source),
        "--destination",
        str(tmp_path),
        "--config",
        str(config),
        "execute-template",
        "--with-stdin",
        "--file",
        str(template),
    ]
    original = {"model": "host-choice", "queuedMessages": "send-immediately", "permissions": {"deny": ["host-rule"]}}
    first = subprocess.run(command, input=json.dumps(original), text=True, capture_output=True, check=True, timeout=30)
    settings = json.loads(first.stdout)
    # agy drops default-valued settings on start, so the host keeps its queue choice.
    assert all(settings[k] == v for k, v in original.items())
    for field, mode in [("statusLine", "statusline"), ("title", "title")]:
        assert settings[field]["enabled"] is True
        arguments = shlex.split(settings[field]["command"])
        assert arguments == ["python3", str(Path.home() / ".agents/skills/agy/scripts/display.py"), mode]
    second = subprocess.run(command, input=first.stdout, text=True, capture_output=True, check=True, timeout=30)
    assert second.stdout == first.stdout


def test_colors_are_owned_by_renderer_and_title_stays_plain() -> None:
    payload = state()
    payload.update(model={"display_name": "Gemini 3.8 Flash (High)\x1b]52;c;private\x07"}, pending_input_count=1)
    colored = render(payload, "statusline", color=True)
    assert display["ANSI"].sub("", colored) == render(payload, "statusline")
    assert "\x1b[1;34m\uf07b dot\x1b[0m" in colored
    assert "\x1b[90m \ue0b1 \x1b[0m" in colored
    assert "Gemini 3.8 Flash (High)" in colored
    assert "1 queued" in colored
    assert "private" not in colored
    assert "\x1b" not in render(payload, "title", color=True)


def test_narrow_display_keeps_activity_and_drops_optional_details() -> None:
    payload = state()
    payload.update(terminal_width=40, tool_confirmation_pending=True)
    text = render(payload, "statusline")
    assert "needs input" in text
    assert "2 tasks" in text
    assert "quota" not in text
    assert "Flash" not in text


def test_wide_display_preserves_full_labels_and_additional_state() -> None:
    payload = state()
    payload.update(
        terminal_width=220,
        model={"display_name": "Gemini 3.8 Flash (High)"},
        execution_mode="planning",
        artifact_count=3,
    )
    text = render(payload, "statusline")
    assert "Gemini 3.8 Flash (High)" in text
    assert "planning" in text
    assert "3 artifacts" in text
    assert "context 24%" in text
    assert "quota min 60% left" in text
    assert "\ue62b INSERT" in text
    payload.update(terminal_width=40, tool_confirmation_pending=True)
    narrow = render(payload, "statusline")
    assert "needs input" in narrow
    assert "artifacts" not in narrow
    assert "planning" not in narrow


@pytest.mark.parametrize("environment", [{"NO_COLOR": "1"}, {"TERM": "dumb"}])
def test_plain_terminal_overrides(environment: dict[str, str]) -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "statusline"],
        input=json.dumps(state()),
        env={**os.environ, **environment},
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    assert "\x1b" not in result.stdout


def test_location_tokens_reset_and_sandbox_details() -> None:
    payload = state()
    payload.update(
        workspace={"project_dir": "/private/owner/dot", "current_dir": "/private/owner/dot/skills/agy"},
        sandbox={"enabled": True, "allow_network": True},
        terminal_width=400,
    )
    text = render(payload, "statusline")
    assert text.startswith("\uf07b dot/skills/agy ")
    assert "sandbox +net" in text
    assert render(payload, "title") == "dot* — working · 2 tasks"
    payload.update(workspace={"project_dir": "/private/owner/dot", "current_dir": "/elsewhere"})
    assert render(payload, "statusline").startswith("\uf07b dot \ue0b1")
    payload.update(workspace={"project_dir": "/private/owner/dot", "current_dir": "/private/owner/dot/x/../../other"})
    assert render(payload, "statusline").startswith("\uf07b dot \ue0b1")


@pytest.mark.parametrize(
    ("mode", "shade"), [("NORMAL", "34"), ("-- INSERT --", "32"), ("-- V-LINE --", "35"), ("REPLACE", "90")]
)
def test_vim_modes_share_colors_by_family(mode: str, shade: str) -> None:
    payload = state()
    payload.update(vim={"mode": mode}, terminal_width=400)
    assert f"\x1b[{shade}m\ue62b {mode}\x1b[0m" in render(payload, "statusline", color=True)


@pytest.mark.parametrize(
    ("count", "expected"),
    [(0, "0"), (999, "999"), (999.6, "1k"), (48_400, "48k"), (1_048_576, "1M"), (1_500_000, "1.5M")],
)
def test_token_counts_stay_compact(count: float, expected: str) -> None:
    assert display["tokens"](count) == expected


@pytest.mark.parametrize(
    ("seconds", "expected"), [(1, "1m"), (3599, "1h00m"), (7500, "2h05m"), (90_000, "1d1h"), (86_400 * 6, "6d0h")]
)
def test_reset_durations_round_up(seconds: float, expected: str) -> None:
    assert display["duration"](seconds) == expected
