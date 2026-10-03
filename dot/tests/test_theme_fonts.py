"""Render font installation paths for both supported workstation platforms."""

import hashlib
import re
import subprocess
import tomllib
from pathlib import Path

import pytest

from dot_tasks import theme_pin

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(("platform", "prefix"), [("linux", ".local/share/fonts"), ("darwin", "Library/Fonts")])
def test_font_installation_targets(platform: str, prefix: str, tmp_path: Path) -> None:
    config = tmp_path / "chezmoi.toml"
    config.write_text("")
    # Render the actual conditional source using synthetic platform data.
    template = '{{ with dict "chezmoi" (dict "os" "' + platform + '") }}\n'
    template += (ROOT / ".chezmoiexternal.toml.tmpl").read_text() + "\n{{ end }}"
    result = subprocess.run(
        ["chezmoi", "--source", str(tmp_path), "--config", str(config), "execute-template"],
        input=template,
        text=True,
        capture_output=True,
        check=True,
        timeout=15,
    )
    assert not result.stderr
    targets = tomllib.loads(result.stdout)
    for family in ("GoogleSans", "GoogleSansCodeOfficial", "GoogleSansCode"):
        entry = targets[f"{prefix}/{family}"]
        assert entry["type"] == "archive"
        assert len(entry["checksum"]["sha256"]) == 64
        assert entry["url"].startswith("https://github.com/")
        assert "/releases/download/v" in entry["url"]
    assert f"{prefix}/GoogleSans-OFL.txt" in targets
    assert "OFL.txt" in targets[f"{prefix}/GoogleSansCodeOfficial"]["include"]


def test_theme_externals_are_pinned_to_one_commit_with_checksums(tmp_path: Path) -> None:
    config = tmp_path / "chezmoi.toml"
    config.write_text("")
    result = subprocess.run(
        ["chezmoi", "--source", str(tmp_path), "--config", str(config), "execute-template"],
        input=(ROOT / ".chezmoiexternal.toml.tmpl").read_text(),
        text=True,
        capture_output=True,
        check=True,
        timeout=15,
    )
    themes = {
        target: entry for target, entry in tomllib.loads(result.stdout).items() if "fmind/theme" in entry.get("url", "")
    }
    # Fish, Neovim, ptpython, and Git execute their theme files.
    assert {".config/fish/conf.d/theme.fish", ".config/nvim/colors/fmind.lua", ".config/git/theme.gitconfig"} <= set(
        themes
    )
    revisions = {re.findall(r"fmind/theme/([0-9a-f]{40})/themes/", entry["url"])[0] for entry in themes.values()}
    assert len(revisions) == 1
    for entry in themes.values():
        assert "refreshPeriod" not in entry
        assert re.fullmatch(r"[0-9a-f]{64}", entry["checksum"]["sha256"])


def test_theme_pin_rewrites_revision_and_checksums() -> None:
    template = (
        '{{ $base := "https://raw.githubusercontent.com/fmind/theme/' + "a" * 40 + '/themes" }}\n'
        '["x"]\n    type = "file"\n    url = "{{ $base }}/fish/fmind.fish"\n    checksum.sha256 = "' + "0" * 64 + '"\n'
    )
    requested: list[str] = []

    def download(url: str) -> bytes:
        requested.append(url)
        return b"theme"

    pinned = theme_pin.pin(template, "b" * 40, download)

    assert requested == ["https://raw.githubusercontent.com/fmind/theme/" + "b" * 40 + "/themes/fish/fmind.fish"]
    assert "b" * 40 in pinned
    assert hashlib.sha256(b"theme").hexdigest() in pinned
    with pytest.raises(ValueError, match="pinned revision"):
        theme_pin.pin(template.replace("a" * 40, "main"), "b" * 40, download)
