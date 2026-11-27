"""Validate Vale anti-slop prose rules and repository starter templates."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import tomllib
from pathlib import Path

import pytest

from repo_helpers import ROOT, native_binary


def _run_vale(vale: Path, config: Path, *targets: Path, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    target_args = [
        str(target.relative_to(cwd)) if cwd is not None and target.is_relative_to(cwd) else str(target)
        for target in targets
    ]
    return subprocess.run(
        [str(vale), "--no-global", "--config", str(config), "--output=JSON", *target_args],
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def test_vale_catches_ai_slop_and_handles_commonmark_edge_cases(tmp_path: Path) -> None:
    vale = native_binary("vale")
    if vale is None:
        if os.environ.get("CI"):
            pytest.fail("Vale binary must be installed in CI via mise.toml")
        pytest.skip("Vale binary is required for live prose-rule verification")

    config = ROOT / "dot_config/vale/dot_vale.ini"
    slop = tmp_path / "slop.md"
    slop.write_text(
        "In today\u2019s fast-paced landscape, we delve into a seamless rollout — a game-changer.\n\n"
        "Il convient de noter qu'on doit utiliser cette méthode afin de pouvoir avancer.\n\n"
        + (" ".join(["word"] * 70))
        + ".\n\n"
        "Avoid `one`, `two`, and `three` backticks in executive prose.\n\n"
        "Merge PR #42 and avoid ClickOps during rollout.\n\n"
        "<code>\u0130</code>`one` `two` `three` still trips backtick spam.\n\n"
        "- top item\n    - nested item with `one`, `two`, and `three` backticks.\n",
        encoding="utf-8",
    )
    slop_readme = tmp_path / "README.md"
    slop_readme.write_text("Unleash the power of this tool after PR #42.\n", encoding="utf-8")
    bad_html = tmp_path / "bad.html"
    bad_html.write_text(
        "<p>Update &mdash; ready now.</p>\n<table><tr><td>Bad — text</td></tr></table>\n", encoding="utf-8"
    )
    bad_htm = tmp_path / "bad.htm"
    bad_htm.write_text("<p>Delve into the release notes.</p>\n", encoding="utf-8")
    bad_typ = tmp_path / "bad.typ"
    bad_typ.write_text("= Delve into this rollout\nFast — seamless launch.\n", encoding="utf-8")

    bad_agents = tmp_path / ".agents" / "AGENTS.md"
    bad_agents.parent.mkdir(parents=True, exist_ok=True)
    bad_agents.write_text("Use separate sentences — never em dashes.\n", encoding="utf-8")

    blocking_run = _run_vale(vale, config, slop, slop_readme, bad_html, bad_htm, bad_typ, bad_agents)
    assert blocking_run.returncode == 1, blocking_run.stdout + blocking_run.stderr
    blocking = json.loads(blocking_run.stdout)
    slop_by_check = {(item["Line"], item["Check"]): item["Severity"] for item in blocking[str(slop)]}
    assert slop_by_check == {
        (1, "Fmind.SlopWords"): "error",
        (1, "Fmind.SlopStyle"): "warning",
        (1, "Fmind.EmDash"): "error",
        (3, "Fmind.SlopWords"): "error",
        (3, "Fmind.Wordiness"): "warning",
        (5, "Fmind.ParagraphLength"): "warning",
        (5, "Fmind.SentenceLength"): "warning",
        (7, "Fmind.ProseBackticks"): "error",
        (9, "Fmind.InternalPlumbing"): "error",
        (11, "Fmind.ProseBackticks"): "error",
        (14, "Fmind.ProseBackticks"): "error",
    }
    assert [(i["Check"], i["Severity"]) for i in blocking[str(slop_readme)]] == [("Fmind.SlopWords", "error")]
    assert [(i["Line"], i["Check"], i["Severity"]) for i in blocking[str(bad_html)]] == [
        (1, "Fmind.EmDash", "error"),
        (2, "Fmind.EmDash", "error"),
    ]
    assert [(i["Check"], i["Severity"]) for i in blocking[str(bad_htm)]] == [("Fmind.SlopWords", "error")]
    assert {(i["Check"], i["Severity"]) for i in blocking[str(bad_typ)]} == {
        ("Fmind.SlopWords", "error"),
        ("Fmind.EmDash", "error"),
        ("Fmind.SlopStyle", "warning"),
    }
    assert [(i["Check"], i["Severity"]) for i in blocking[str(bad_agents)]] == [("Fmind.EmDash", "error")]

    advisory = tmp_path / "advisory.md"
    advisory.write_text(
        "We leverage seamless cutting-edge synergy in order to utilize failover; a testament to tests.\n\n"
        "Dans le cadre de ce suivi, on a daily basis, il convient de souligner un point clair.\n\n"
        + (" ".join(["mot"] * 33))
        + ". "
        + (" ".join(["mot"] * 25))
        + ".\n",
        encoding="utf-8",
    )
    advisory_run = _run_vale(vale, config, advisory)
    assert advisory_run.returncode == 0, advisory_run.stdout + advisory_run.stderr
    assert {(i["Check"], i["Severity"]) for i in json.loads(advisory_run.stdout)[str(advisory)]} == {
        ("Fmind.SlopStyle", "warning"),
        ("Fmind.Wordiness", "warning"),
        ("Fmind.SentenceLength", "warning"),
        ("Fmind.ParagraphLength", "warning"),
    }

    clean_files = {
        tmp_path / "clean.md": (
            '---\ndescription: "Flags `--one`, `--two`, and `--three` in YAML frontmatter."\n---\n\n'
            "<!-- Single-line note with `one`, `two`, and `three` ignored. -->\n\n"
            "<!--\n  Multi-line note with `one`, `two`, and `three` ignored.\n-->\n\n"
            "**Batch imports are healthy again: approve PR 418 before 17:00 UTC.**\n\n"
            "We deploy Unleash for feature flags, debug Go binaries with Delve, differentiate with respect to weights, "
            "parse `<!--` literals, and track CPU utilization.\n\n"
            "Peak memory stays below our 8 GB limit. Inline `code — ok` and ``cmd `a` `b` `c` `` pass.\n\n"
            "Escaped \\`one\\`, \\`two\\`, and \\`three\\` plus <code>`a`</code>, <code>`b`</code>, <code>`c`</code> pass.\n\n"
            "    indented `code` block `with` three `backticks` here\n\n"
            "Col A | Col B\n--- | ---\n`a` | `b` and `c`\n\n"
            "| Metric | Value |\n| --- | --- |\n| Latency | — |\n\n"
            "L'équipe d'ingénierie n'a pas encore validé l'architecture d'aujourd'hui, c'est-à-dire qu'elle "
            "doit contrôler l'état du sous-système, s'assurer qu'il n'y a pas d'anomalie critique, "
            "et mettre à jour l'outil d'ici demain.\n\n" + (" ".join(["don't"] * 21)) + ".\n\n"
            "> ```bash\n> echo `one` and `two` and `three`\n> ```\n\n"
            "````markdown\n```bash\nChecked `one` and `two` and `three` inside nested fence.\n```\n````\n\n"
            "```markdown\n    ```\nStill inside fence with `one`, `two`, and `three`.\n```\n"
        ),
        tmp_path / "toml_frontmatter.md": '+++\ntitle = "Use `a`, `b`, and `c`"\n+++\n\nClean body.\n',
        tmp_path / "sub" / "README.md": "Run `one`, `two`, and `three` in terminal.\n",
        tmp_path / "docs" / "guide.md": "Pass `--one`, `--two`, and `--three` to the CLI.\n",
        tmp_path / "notes.txt": "Run `a`, `b`, and `c`.\n",
        tmp_path / "component.mdx": "export const msg = `${a}` + `${b}` + `${c}`;\n\nClean copy.\n",
        tmp_path / "AGENTS.md": "Use `one`, `two`, and `three`. Keep diffs small.\n",
        tmp_path / "GEMINI.md": "Use `one`, `two`, and `three` — keep diffs small.\n",
        tmp_path / ".gemini" / "rules.md": "Use `one`, `two`, and `three` — keep diffs small.\n",
        tmp_path / "copilot-instructions.md": "Use `one`, `two`, and `three` — keep diffs small.\n",
        tmp_path / "skills" / "demo" / "SKILL.md": "Use `one`, `two`, and `three` — keep diffs small.\n",
        tmp_path
        / ".venv"
        / "lib"
        / "pkg"
        / "LICENSE.txt": "Granted for the purpose of testing — delve into nothing.\n",
        tmp_path / "node_modules" / "pkg" / "README.md": "Unleash the power of this dependency.\n",
        tmp_path / "page.html": (
            "<!doctype html><p>Clean outcome.</p><code>&mdash;</code>"
            "<table><tr><td>Latency</td><td>—</td><td>&mdash;</td></tr></table>"
            "<script>const s = `${a}` + `${b}` + `${c}`;</script>\n"
        ),
    }
    for path, content in clean_files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    clean_run = _run_vale(vale, config, *clean_files)
    assert clean_run.returncode == 0, clean_run.stdout + clean_run.stderr
    assert json.loads(clean_run.stdout) == {}


def test_vale_accepts_external_starter_markdown_templates() -> None:
    vale = native_binary("vale")
    if vale is None:
        if os.environ.get("CI"):
            pytest.fail("Vale binary must be installed in CI via mise.toml")
        pytest.skip("Vale binary is required for external template verification")

    vale_cmd = tomllib.loads((ROOT / "mise.toml").read_text(encoding="utf-8"))["tasks"]["check:vale"]["run"]
    tokens = shlex.split(vale_cmd)
    skip_next = False
    templates: list[Path] = []
    for tok in tokens[1:]:
        if skip_next:
            skip_next = False
            continue
        if tok == "--config":
            skip_next = True
            continue
        if tok.startswith("-"):
            continue
        target = ROOT / tok
        if target.is_dir():
            templates.extend(sorted(p for p in target.rglob("*") if p.is_file() and p.suffix in {".md", ".html"}))
        else:
            templates.append(target)
    assert ROOT / "README.md" in templates
    result = _run_vale(vale, ROOT / ".vale.ini", *templates, cwd=ROOT)
    assert result.returncode == 0, f"{result.stdout}{result.stderr}"
    errors = [item for items in json.loads(result.stdout).values() for item in items if item["Severity"] == "error"]
    assert errors == [], f"unexpected Vale errors: {errors}"

    # Absolute-path invocations (as used by editors) must honor repo .vale.ini overrides.
    abs_skills = [
        ROOT / "skills/python/SKILL.md",
        ROOT / ".agents/skills/chezmoi/SKILL.md",
    ]
    abs_compiled = ROOT / "private_dot_gemini/private_config/agents/fmind-review-code.md"
    abs_result = _run_vale(vale, ROOT / ".vale.ini", *abs_skills, abs_compiled)
    assert abs_result.returncode == 0, f"{abs_result.stdout}{abs_result.stderr}"
    abs_findings = json.loads(abs_result.stdout)
    assert abs_findings.get(str(abs_compiled), []) == [], (
        f"expected Fmind=NO for compiled agent: {abs_findings.get(str(abs_compiled))}"
    )
    suppressed = {"Fmind.EmDash", "Fmind.ParagraphLength", "Fmind.SentenceLength"}
    for skill_path in abs_skills:
        skill_items = abs_findings.get(str(skill_path), [])
        leaked = [i for i in skill_items if i["Severity"] == "error" or i["Check"] in suppressed]
        assert leaked == [], f"unexpected Vale alerts on {skill_path.relative_to(ROOT)}: {leaked}"


def test_repo_vale_config_still_enforces_em_dash_on_relocated_starter_templates(tmp_path: Path) -> None:
    vale = native_binary("vale")
    if vale is None:
        if os.environ.get("CI"):
            pytest.fail("Vale binary must be installed in CI via mise.toml")
        pytest.skip("Vale binary is required for external template regression verification")

    cfg = (
        (ROOT / ".vale.ini")
        .read_text(encoding="utf-8")
        .replace(
            "StylesPath = dot_config/vale/styles",
            f"StylesPath = {ROOT / 'dot_config/vale/styles'}",
        )
    )
    (tmp_path / ".vale.ini").write_text(cfg, encoding="utf-8")
    for rel, expect_extra in (
        ("skills/docs/references/repository/templates/README.md", False),
        ("skills/docs/references/site/templates/index.md", True),
        ("skills/python/references/foundation/templates/docs-index.md", True),
    ):
        probe = tmp_path / rel
        probe.parent.mkdir(parents=True, exist_ok=True)
        probe.write_text(
            "This starter has an em dash — which must fail.\n\n"
            "Avoid `one`, `two`, and `three` backticks after PR #42.\n",
            encoding="utf-8",
        )
        res = _run_vale(vale, tmp_path / ".vale.ini", probe, cwd=tmp_path)
        assert res.returncode == 1, f"{rel}: expected Vale failure, got rc=0"
        checks = {item["Check"] for items in json.loads(res.stdout).values() for item in items}
        assert "Fmind.EmDash" in checks
        if expect_extra:
            assert {"Fmind.ProseBackticks", "Fmind.InternalPlumbing"} <= checks
