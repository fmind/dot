"""Render font installation paths for both supported workstation platforms."""

import hashlib
import http.client
import io
import re
import subprocess
import threading
import tomllib
from pathlib import Path

import pytest

from dot_tasks import theme_pin
from repo_helpers import ROOT, chezmoi


@pytest.mark.parametrize(("platform", "prefix"), [("linux", ".local/share/fonts"), ("darwin", "Library/Fonts")])
def test_font_installation_targets(platform: str, prefix: str, tmp_path: Path) -> None:
    # Render the actual conditional source using synthetic platform data.
    template = '{{ with dict "chezmoi" (dict "os" "' + platform + '") }}\n'
    template += (ROOT / ".chezmoiexternal.toml.tmpl").read_text() + "\n{{ end }}"
    targets = tomllib.loads(chezmoi(tmp_path, "execute-template", stdin=template))
    for family in ("GoogleSans", "GoogleSansCodeOfficial", "GoogleSansCode"):
        entry = targets[f"{prefix}/{family}"]
        assert entry["type"] == "archive"
        assert len(entry["checksum"]["sha256"]) == 64
        assert entry["url"].startswith("https://github.com/")
        assert "/releases/download/v" in entry["url"]
    assert f"{prefix}/GoogleSans-OFL.txt" in targets
    assert "OFL.txt" in targets[f"{prefix}/GoogleSansCodeOfficial"]["include"]


def test_theme_externals_are_pinned_to_one_commit_with_checksums(tmp_path: Path) -> None:
    template = (ROOT / ".chezmoiexternal.toml.tmpl").read_text()
    rendered = tomllib.loads(chezmoi(tmp_path, "execute-template", stdin=template))
    themes = {target: entry for target, entry in rendered.items() if "fmind/theme" in entry.get("url", "")}
    # Neovim and Git execute their theme files; fish and agents read data files.
    assert {
        ".agents/DESIGN.md",
        ".config/fish/themes/fmind.theme",
        ".config/nvim/colors/fmind.lua",
        ".config/git/theme.gitconfig",
        ".config/git/colors.gitconfig",
    } <= set(themes)
    revisions = {re.findall(r"fmind/theme/([0-9a-f]{40})/", entry["url"])[0] for entry in themes.values()}
    assert len(revisions) == 1
    for entry in themes.values():
        assert "refreshPeriod" not in entry
        assert re.fullmatch(r"[0-9a-f]{64}", entry["checksum"]["sha256"])


def test_skills_reference_only_deployed_theme_files(tmp_path: Path) -> None:
    # Skills copy renderer files from ~/.agents/themes/ instead of carrying palette values.
    template = (ROOT / ".chezmoiexternal.toml.tmpl").read_text()
    targets = set(tomllib.loads(chezmoi(tmp_path, "execute-template", stdin=template)))
    referenced = {
        match.removeprefix("~/")
        for path in (ROOT / "skills").rglob("*")
        if path.suffix in {".md", ".tape"} and path.is_file()
        for match in re.findall(r"~/\.agents/themes/[\w-]+/[\w.-]+\.\w+", path.read_text(encoding="utf-8"))
    }
    assert referenced
    assert referenced <= targets


def test_theme_pin_rewrites_revision_and_checksums() -> None:
    template = '{{ $base := "https://raw.githubusercontent.com/fmind/theme/' + "a" * 40 + '" }}\n'
    for path in ("themes/fish/fmind.fish", "DESIGN.md"):
        template += (
            f'["{path}"]\n    type = "file"\n    url = "{{{{ $base }}}}/{path}"\n    checksum.sha256 = "{"0" * 64}"\n'
        )
    requested: list[str] = []

    def download(url: str) -> bytes:
        requested.append(url)
        return b"theme"

    pinned = theme_pin.pin(template, "b" * 40, download)

    raw = "https://raw.githubusercontent.com/fmind/theme/" + "b" * 40
    assert requested == [raw + "/themes/fish/fmind.fish", raw + "/DESIGN.md"]
    assert "0" * 64 not in pinned
    assert "b" * 40 in pinned
    assert hashlib.sha256(b"theme").hexdigest() in pinned
    with pytest.raises(ValueError, match="pinned revision"):
        theme_pin.pin(template.replace("a" * 40, "main"), "b" * 40, download)


def test_theme_prefetch_downloads_distinct_urls_concurrently(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(theme_pin, "COPIED", {"dot_config/starship.toml": ("themes/starship/fmind.toml", ())})
    monkeypatch.setattr(theme_pin, "RAW_COPIES", {"skills/draft/fmind.typ": "themes/typst/fmind.typ"})
    template = '{{ $base := "https://raw.githubusercontent.com/fmind/theme/' + "a" * 40 + '" }}\n'
    for path in ("themes/fish/fmind.fish", "themes/starship/fmind.toml"):
        template += (
            f'["{path}"]\n    type = "file"\n    url = "{{{{ $base }}}}/{path}"\n    checksum.sha256 = "{"0" * 64}"\n'
        )
    barrier = threading.Barrier(3, timeout=5)
    calls: list[str] = []

    def download(url: str) -> bytes:
        calls.append(url)
        if len(calls) <= 3:
            barrier.wait()
        return url.encode()

    cached = theme_pin.prefetch("b" * 40, template, download)
    raw = "https://raw.githubusercontent.com/fmind/theme/" + "b" * 40
    assert len(calls) == 3
    assert cached(f"{raw}/themes/starship/fmind.toml") == f"{raw}/themes/starship/fmind.toml".encode()
    assert cached(f"{raw}/themes/typst/fmind.typ") == f"{raw}/themes/typst/fmind.typ".encode()
    assert len(calls) == 3
    assert cached(f"{raw}/other") == f"{raw}/other".encode()
    assert len(calls) == 4
    assert theme_pin.prefetch("b" * 40, "no entries", download) is download


def test_copied_theme_registry_covers_every_upstream_copy() -> None:
    result = subprocess.run(
        ["git", "grep", "--untracked", "-l", "fmind/theme/blob/main/themes/", "--", ":!dot/"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
        timeout=15,
    )
    assert set(result.stdout.split()) == set(theme_pin.COPIED)


def test_stale_copies_detects_changed_and_missing_theme_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    source = "dot_config/starship.toml"
    monkeypatch.setattr(theme_pin, "COPIED", {source: ("themes/starship/fmind.toml", (("palette",), ("palettes",)))})
    local = (ROOT / source).read_text()

    def check(upstream: str) -> list[str]:
        return theme_pin.stale_copies("b" * 40, lambda _url: upstream.encode(), lambda path: path.read_text())

    assert check(local) == []
    assert check(local.replace('blue = "#174ea6"', 'blue = "#000000"')) == [
        f"{source}: palettes differs from themes/starship/fmind.toml"
    ]
    assert check(local.replace('palette = "fmind"', "")) == [
        f"{source}: palette differs from themes/starship/fmind.toml"
    ]


def test_stale_raw_copies_detects_changed_typst_file() -> None:
    expected = (ROOT / "skills/draft/references/typst-deck/templates/fmind.typ").read_bytes()
    assert theme_pin.stale_raw_copies("b" * 40, lambda _url: expected) == []
    assert theme_pin.stale_raw_copies("b" * 40, lambda _url: b"stale") == [
        "skills/draft/references/typst-deck/templates/fmind.typ: differs from themes/typst/fmind.typ"
    ]


def test_copied_theme_parsers_ignore_comments() -> None:
    assert theme_pin.parse("--hidden\n--colors=path:style:bold\n", "ripgrep/fmind.ripgreprc") == {
        "colors": ["--colors=path:style:bold"]
    }
    assert "theme = fmind" in theme_pin.render(ROOT / "dot_config/ghostty/config.tmpl")
    assert 'palette = "fmind"' in theme_pin.render(ROOT / "dot_config/starship.toml")


def test_theme_pin_handles_fetch_limits_resolution_and_main_failures(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sha = "c" * 40
    monkeypatch.setattr(
        theme_pin.subprocess,
        "run",
        lambda *_a, **_kw: subprocess.CompletedProcess([], 0, stdout=f"{sha}\trefs/heads/main\n", stderr=""),
    )
    assert theme_pin.resolve_head() == sha

    monkeypatch.setattr(
        theme_pin.subprocess,
        "run",
        lambda *_a, **_kw: subprocess.CompletedProcess([], 0, stdout="bad\n", stderr=""),
    )
    with pytest.raises(ValueError, match="cannot resolve"):
        theme_pin.resolve_head()

    monkeypatch.setattr(
        theme_pin.urllib.request, "urlopen", lambda *_a, **_kw: io.BytesIO(b"x" * (theme_pin.MAX_BYTES + 1))
    )
    with pytest.raises(ValueError, match="exceeds"):
        theme_pin.fetch("https://example.test/theme")

    with pytest.raises(ValueError, match="unsupported theme format"):
        theme_pin.parse("data", "theme.txt")

    (tmp_path / ".chezmoiexternal.toml.tmpl").write_text("", encoding="utf-8")
    monkeypatch.setattr(theme_pin, "ROOT", tmp_path)
    monkeypatch.setattr("sys.argv", ["theme_pin", "--revision", sha])
    monkeypatch.setattr(
        theme_pin,
        "prefetch",
        lambda *_a: (_ for _ in ()).throw(http.client.HTTPException("upstream timeout")),
    )
    assert theme_pin.main() == 1
    assert "Cannot pin fmind/theme: upstream timeout" in capsys.readouterr().err

    # fetch happy path, pin missing ENTRY, parse YAML, invalid --revision exit 2, stale copies, and clean update/no-op
    monkeypatch.setattr(theme_pin.urllib.request, "urlopen", lambda *_a, **_kw: io.BytesIO(b"hello-theme"))
    assert theme_pin.fetch("https://example.test/theme") == b"hello-theme"

    base_only = '{{ $base := "https://raw.githubusercontent.com/fmind/theme/' + "a" * 40 + '" }}\n'
    with pytest.raises(ValueError, match="no checksummed theme entries"):
        theme_pin.pin(base_only, sha, lambda _u: b"x")

    monkeypatch.setattr("sys.argv", ["theme_pin", "--revision", "not-a-sha"])
    with pytest.raises(SystemExit) as bad_rev:
        theme_pin.main()
    assert bad_rev.value.code == 2

    tmpl = (
        '{{ $base := "https://raw.githubusercontent.com/fmind/theme/'
        + "a" * 40
        + '" }}\n'
        + '["themes/fish/fmind.fish"]\n    type = "file"\n    url = "{{ $base }}/themes/fish/fmind.fish"\n'
        + f'    checksum.sha256 = "{"0" * 64}"\n'
    )
    ext_file = tmp_path / ".chezmoiexternal.toml.tmpl"
    ext_file.write_text(tmpl, encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["theme_pin", "--revision", sha])
    monkeypatch.setattr(theme_pin, "prefetch", lambda *_a: lambda _u: b"theme-bytes")
    monkeypatch.setattr(theme_pin, "stale_raw_copies", lambda *_a: [])
    monkeypatch.setattr(theme_pin, "stale_copies", lambda *_a: ["dot_config/starship.toml: stale"])
    assert theme_pin.main() == 1
    assert "Copy the upstream blocks" in capsys.readouterr().err
    assert ext_file.read_text(encoding="utf-8") == tmpl

    monkeypatch.setattr(theme_pin, "stale_copies", lambda *_a: [])
    assert theme_pin.main() == 0
    assert f"fmind/theme pinned to {sha}" in capsys.readouterr().out
    pinned_text = ext_file.read_text(encoding="utf-8")
    assert sha in pinned_text
    assert theme_pin.main() == 0
    assert ext_file.read_text(encoding="utf-8") == pinned_text
