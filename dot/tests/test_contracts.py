from __future__ import annotations

import fnmatch
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from dot_tasks import skill_contracts as checker
from dot_tasks.mise_refresh import validate
from fmind_dot import privacy
from repo_helpers import ROOT, chezmoi


def _write_skill(
    root: Path, *, name: str = "fixture", description: str = "Validate a compact fixture. Use for contract tests."
) -> Path:
    d = root / "skills" / name
    (d / "references").mkdir(parents=True, exist_ok=True)
    skill = d / "SKILL.md"
    skill.write_text(
        f"---\nname: {name}\ndescription: {description}\nlicense: MIT\nmetadata:\n  kind: task\n"
        f"  author: Fixture Author\n  source: github.com/fmind/dot/tree/main/skills/{name}\n"
        '  created: "2026-10-01"\n  updated: "2026-10-12"\n---\n\n# Fixture\n\nUse uv.\n\n'
        "## Workflow\n\n1. Run.\n\n## Documentation\n\n- [Reference](references/guide.md)\n",
        encoding="utf-8",
    )
    (d / "references/guide.md").write_text("# Guide\n", encoding="utf-8")
    return skill


def _repo(tmp_path: Path) -> Path:
    _write_skill(tmp_path)
    _write_skill(tmp_path, name="fixture-helper", description="Support fixtures. Use for secondary route tests.")
    (tmp_path / "README.md").write_text("# Fixture\n\nPython implementation.\n", encoding="utf-8")
    (tmp_path / "dot_agents").mkdir()
    (tmp_path / "dot_agents/AGENTS.md").write_text("# Fixture instructions\n", encoding="utf-8")
    return tmp_path


def test_skills_contract_accepts_valid_repo_and_flags_collisions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path)
    assert checker.repository_findings(root) == []

    broken = root / "skills/fixture/SKILL.md"
    broken.write_text(broken.read_text(encoding="utf-8").replace("name: fixture", "name: wrong"), encoding="utf-8")
    dup = root / ".agents/skills/fixture"
    dup.mkdir(parents=True)
    (dup / "SKILL.md").write_text(
        "---\nname: fixture\ndescription: Duplicate fixture.\nlicense: MIT\nmetadata:\n  kind: task\n"
        '  author: Author\n  source: github.com/fmind/dot/tree/main/.agents/skills/fixture\n  created: "2026-10-01"\n'
        '  updated: "2026-10-12"\n---\n\n# Fixture\n',
        encoding="utf-8",
    )
    findings = checker.repository_findings(root)
    assert any("skills/fixture/SKILL.md" in f and "must match its directory" in f for f in findings)
    assert any("duplicate skill directory 'fixture'" in f for f in findings)
    monkeypatch.setattr(checker, "ROOT", root)
    monkeypatch.setattr("sys.argv", ["skill_contracts", "--sync"])
    assert checker.main() == 1


@pytest.mark.parametrize("value", ["true", "false", '"true"', "1", "null"])
def test_skills_contract_checks_explicit_invocation_boolean(tmp_path: Path, value: str) -> None:
    root = _repo(tmp_path)
    skill = root / "skills/fixture/SKILL.md"
    skill.write_text(skill.read_text().replace("license: MIT", f"license: MIT\ndisable-model-invocation: {value}"))
    findings = checker.repository_findings(root)
    if value in {"true", "false"}:
        assert findings == []
    else:
        assert any("disable-model-invocation must be a boolean" in f for f in findings)


@pytest.mark.parametrize(
    ("orig", "repl", "expected"),
    [
        ("name: fixture", "name: wrong", "must match its directory"),
        ("  kind: task", "  kind: task\n  deep: " + "[" * 1000 + "]" * 1000, "invalid frontmatter"),
        ("  author: Fixture Author\n", "", "metadata.author must be a non-empty string"),
        ("  author: Fixture Author", "  author: 42", "metadata keys and values must be strings"),
        ("  author: Fixture Author", '  author: ""', "metadata.author must be a non-empty string"),
        ("  source: github.com/fmind/dot/tree/main/skills/fixture", "  source: null", "metadata.source"),
        (
            "  source: github.com/fmind/dot/tree/main/skills/fixture",
            "  source: github.com/fmind/dot/tree/main/skills/other",
            "metadata.source",
        ),
        ('  created: "2026-10-01"', "  created: 2026-10-01", "metadata keys and values must be strings"),
        ('  updated: "2026-10-12"\n', "", "metadata.updated must be a non-empty string"),
        ('  updated: "2026-10-12"', '  updated: "2026-13-40"', "must be a valid YYYY-MM-DD date"),
        ('  updated: "2026-10-12"', '  updated: "2026-09-01"', "precedes metadata.created"),
        ("  kind: task", "  kind: unknown", "metadata.kind must"),
        ("  kind: task", "  kind: []", "metadata.kind must"),
        ("  kind: task", "  kind: {}", "metadata.kind must"),
        ("  kind: task", "  kind: null", "metadata.kind must"),
        ("  kind: task", "  kind: task\n  1: value", "metadata keys and values must be strings"),
    ],
)
def test_skills_contract_rejects_invalid_frontmatter_and_metadata(
    tmp_path: Path, orig: str, repl: str, expected: str
) -> None:
    root = _repo(tmp_path)
    skill = root / "skills/fixture/SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8").replace(orig, repl), encoding="utf-8")
    assert any(expected in f for f in checker.repository_findings(root))


def test_skills_contract_flags_stale_updated_date_since_release_tag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path)
    local_skill = root / ".agents/skills/local-helper"
    (local_skill / "references").mkdir(parents=True)
    (local_skill / "SKILL.md").write_text(
        "---\nname: local-helper\ndescription: Local repo helper.\nlicense: MIT\nmetadata:\n  kind: task\n"
        "  author: Fixture Author\n  source: github.com/fmind/dot/tree/main/.agents/skills/local-helper\n"
        '  created: "2026-10-01"\n  updated: "2026-10-12"\n---\n\n# Local\n\n- [Ref](references/ref.md)\n',
        encoding="utf-8",
    )
    (local_skill / "references/ref.md").write_text("# Ref\n", encoding="utf-8")
    env = {
        **{k: v for k, v in os.environ.items() if k not in {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"}},
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_AUTHOR_NAME": "Fixture",
        "GIT_AUTHOR_EMAIL": "fixture@example.com",
        "GIT_COMMITTER_NAME": "Fixture",
        "GIT_COMMITTER_EMAIL": "fixture@example.com",
    }

    def git(*args: str, extra_env: dict[str, str] | None = None) -> None:
        res = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True, check=False, env=env | (extra_env or {})
        )
        assert res.returncode == 0, res.stderr

    git("init", "-q", "-b", "main")
    git("add", ".")
    git("commit", "-q", "-m", "chore: init")
    git("tag", "v1.0.0")
    assert checker.repository_findings(root) == []

    # Editing a reference without bumping metadata.updated must fail (both skills/ and .agents/skills/).
    (root / "skills/fixture/references/guide.md").write_text("# Guide\n\nUpdated guidance.\n", encoding="utf-8")
    (local_skill / "references/ref.md").write_text("# Ref\n\nUpdated local.\n", encoding="utf-8")
    stale = checker.repository_findings(root)
    assert any("skills/fixture/SKILL.md: metadata.updated ('2026-10-12') must be bumped" in f for f in stale)
    assert any(
        ".agents/skills/local-helper/SKILL.md: metadata.updated ('2026-10-12') must be bumped" in f for f in stale
    )

    # Committed stale edit on a later commit date still fails; same-day edit does not.
    git("add", "skills/fixture/references/guide.md")
    git(
        "commit",
        "-q",
        "-m",
        "docs(skills): stale commit",
        extra_env={"GIT_AUTHOR_DATE": "2026-10-15T12:00:00Z", "GIT_COMMITTER_DATE": "2026-10-15T12:00:00Z"},
    )
    committed_stale = checker.repository_findings(root)
    assert any("skills/fixture/SKILL.md: metadata.updated ('2026-10-12') must be bumped" in f for f in committed_stale)

    # New skill added since v1.0.0 is exempt (no base tag entry).
    _write_skill(root, name="brand-new")

    # Bumping metadata.updated clears the findings, both uncommitted and committed.
    for path in (root / "skills/fixture/SKILL.md", local_skill / "SKILL.md"):
        path.write_text(path.read_text(encoding="utf-8").replace("2026-10-12", "2026-11-24"), encoding="utf-8")
    assert checker.repository_findings(root) == []
    git("add", ".")
    git("commit", "-q", "-m", "docs(skills): update fixture")
    assert checker.repository_findings(root) == []

    # Shallow CI clone missing v* tags fails closed instead of silently skipping freshness checks.
    shallow = tmp_path / "shallow"
    res = subprocess.run(
        ["git", "clone", "--depth", "1", "--no-tags", f"file://{root}", str(shallow)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert res.returncode == 0, res.stderr
    monkeypatch.setenv("CI", "true")
    assert any("shallow CI clone" in f for f in checker.repository_findings(shallow))


@pytest.mark.parametrize(
    ("rel", "content", "expected"),
    [
        ("references/control.md", b"safe\x1b[2Jspoofed\n", "unsafe control character"),
        ("references/bidi.md", "safe\u202ehidden\n".encode(), "invisible Unicode"),
        ("references/tags.md", "safe\U000e0069\U000e0067hidden\n".encode(), "invisible Unicode"),
        ("references/selectors.md", "safe\ufe00\U000e0100hidden\n".encode(), "invisible Unicode"),
        ("references/binary.md", b"text\x00payload\n", "unsafe control character"),
        ("references/non-utf8.md", b"text\xffpayload\n", "is not UTF-8"),
        ("SKILL.md", None, "invisible Unicode"),
    ],
)
def test_skills_contract_rejects_unsafe_text(tmp_path: Path, rel: str, content: bytes | None, expected: str) -> None:
    root = _repo(tmp_path)
    target = root / "skills/fixture" / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    if content is None:
        target.write_text(target.read_text(encoding="utf-8") + "\nHidden\u202etext\n", encoding="utf-8")
    else:
        target.write_bytes(content)
    assert any(expected in f for f in checker.repository_findings(root))


def test_skills_contract_resource_reachability_permissions_and_symlinks(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    skill = root / "skills/fixture"
    (skill / "references/hidden.md").write_text("# Hidden\n", encoding="utf-8")
    (skill / "assets").mkdir()
    exe = skill / "assets/generator"
    exe.write_text("#!/bin/sh\n", encoding="utf-8")
    exe.chmod(0o755)
    target = skill / "outside.py"
    target.write_text("print('x')\n", encoding="utf-8")
    (skill / "scripts").mkdir()
    (skill / "scripts/payload.py").symlink_to(target)
    os.mkfifo(skill / "references/runtime.pipe")
    (skill / "references/child").mkdir()
    (skill / "references/child/SKILL.md").write_text("# Child\n", encoding="utf-8")
    (skill / "references/guide.md").write_text("[P](proc.md) [C](child/SKILL.md)\n", encoding="utf-8")
    (skill / "references/proc.md").write_text("[T](tmpl.txt)\n", encoding="utf-8")
    (skill / "references/tmpl.txt").write_text("ok\n", encoding="utf-8")
    findings = checker.repository_findings(root)
    for expected in ("not reachable", "executable outside scripts", "symbolic link", "non-regular", "nested SKILL.md"):
        assert any(expected in f for f in findings), findings


@pytest.mark.parametrize("entry", ["---\nname: linked\n---\n", "foreign\n"], ids=["skill", "foreign"])
def test_skills_contract_rejects_symlinked_and_orphan_roots(tmp_path: Path, entry: str) -> None:
    root = _repo(tmp_path)
    outside = root / "outside"
    outside.mkdir()
    (outside / "SKILL.md").write_text(entry, encoding="utf-8")
    (root / "skills/linked").symlink_to(outside, target_is_directory=True)
    assert any("symbolic link" in f for f in checker.repository_findings(root))
    (root / "skills/linked").unlink()
    (root / "skills/empty/references").mkdir(parents=True)
    assert checker.repository_findings(root) == []
    (root / "skills/empty/references/g.md").write_text("# O\n", encoding="utf-8")
    assert checker.repository_findings(root) == ["skills/empty: skill root has files but no SKILL.md"]


def test_repository_skills_have_individual_chezmoi_links() -> None:
    packages = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
    links = ROOT / "dot_agents/skills"
    assert {p.name for p in links.iterdir()} == {f"symlink_{name}.tmpl" for name in packages}
    for name in packages:
        assert (links / f"symlink_{name}.tmpl").read_text() == "{{ .chezmoi.sourceDir }}/skills/" + name + "\n"


@pytest.mark.parametrize(("scope", "relative"), [("global", "dot_agents/AGENTS.md"), ("local", "AGENTS.md")])
def test_skills_contract_budgets_and_duplicate_names(tmp_path: Path, scope: str, relative: str) -> None:
    root = _repo(tmp_path)
    (root / ".agents/skills").mkdir(parents=True)
    moved = root / ".agents/skills/fixture-helper"
    (root / "skills/fixture-helper").rename(moved)
    moved_skill = moved / "SKILL.md"
    moved_skill.write_text(
        moved_skill.read_text(encoding="utf-8").replace(
            "tree/main/skills/fixture-helper", "tree/main/.agents/skills/fixture-helper"
        ),
        encoding="utf-8",
    )
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x" * 20_000)
    findings = checker.repository_findings(root)
    assert any(f"{scope} AGENTS.md + skill discovery contains" in f for f in findings)
    path.write_text("Short.\n")
    assert checker.repository_findings(root) == []

    sub_root = root / ("dot_agents/supagents" if scope == "global" else ".agents/supagents")
    sub_root.mkdir(parents=True, exist_ok=True)
    sub_file = sub_root / "fixture-review.md"
    sub_file.write_text("---\nname: fixture-review\ndescription: " + "r" * 8_000 + "\n---\n# Rubric\n")
    sub_findings = checker.repository_findings(root)
    assert any(f"{scope} subagent discovery contains" in f for f in sub_findings)
    sub_file.write_text("---\nname: fixture-review\ndescription: Review fixtures.\n---\n# Rubric\n")
    assert checker.repository_findings(root) == []

    other_sub = root / (".agents/supagents" if scope == "global" else "dot_agents/supagents") / "fixture-review.md"
    other_sub.parent.mkdir(parents=True, exist_ok=True)
    other_sub.write_text(sub_file.read_text())
    sub_dup = checker.repository_findings(root)
    assert any(
        f.startswith("agent context: duplicate subagent name 'fixture-review' in ") and "Rename" in f for f in sub_dup
    )
    other_sub.unlink()

    nested = root / ".agents/skills/fixture-helper/extra/fixture/SKILL.md"
    nested.parent.mkdir(parents=True)
    nested.write_text((root / "skills/fixture/SKILL.md").read_text())
    dup = checker.repository_findings(root)
    assert any(f.startswith("agent context: duplicate skill name 'fixture' in ") and "Rename" in f for f in dup)


def test_skills_guide_contracts_and_promotion(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    skill = root / "skills/fixture/SKILL.md"
    guide = skill.parent / "references/guide.md"
    guide.write_text("---\nname: guide\ndescription: Diagnose a fixture failure.\n---\n# Guide\n")
    expected_index = (
        "<!-- guides:start -->\n\n- [guide](references/guide.md): Diagnose a fixture failure.\n\n<!-- guides:end -->"
    )
    assert checker._guide_index(skill.parent, root) == expected_index
    skill.write_text(skill.read_text() + "\n" + expected_index + "\n")
    assert checker.repository_findings(root) == []
    guide.write_text(guide.read_text().replace("Diagnose a fixture failure.", "Recover after failure."))
    assert any("stale guide index" in f for f in checker.repository_findings(root))
    skill.write_text(skill.read_text().replace(checker.GUIDE_START, "").replace(checker.GUIDE_END, ""))
    assert any("add <!-- guides:start -->" in f for f in checker.repository_findings(root))

    root2 = _repo(tmp_path / "promo")
    parent = root2 / "skills/fixture"
    cg = parent / "references/child/GUIDE.md"
    cg.parent.mkdir()
    cg.write_text("---\nname: child\ndescription: Recover.\n---\n# Child\n[input](templates/input.txt)\n")
    (cg.parent / "templates").mkdir()
    (cg.parent / "templates/input.txt").write_text("in\n")
    (parent / "SKILL.md").write_text(
        (parent / "SKILL.md").read_text()
        + "\n<!-- guides:start -->\n\n- [child](references/child/GUIDE.md): Recover.\n\n<!-- guides:end -->\n"
    )
    assert checker.repository_findings(root2) == []


@pytest.mark.parametrize("guide_name", ["fixture", "fixture-cli", "headless-fixture", "sub-fixture-guide"])
def test_skills_contract_rejects_guide_repeating_parent(tmp_path: Path, guide_name: str) -> None:
    root = _repo(tmp_path)
    skill = root / "skills/fixture/SKILL.md"
    (skill.parent / f"references/{guide_name}.md").write_text(
        f"---\nname: {guide_name}\ndescription: Repeat parent.\n---\n# G\n"
    )
    skill.write_text(
        skill.read_text()
        + f"\n<!-- guides:start -->\n\n- [{guide_name}](references/{guide_name}.md): Repeat parent.\n\n<!-- guides:end -->\n"
    )
    assert any("must not repeat its parent skill" in f for f in checker.repository_findings(root))


def test_skills_markdown_budgets_and_sync_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _repo(tmp_path)
    skill = root / "skills/fixture/SKILL.md"
    refs = skill.parent / "references"
    (refs / "templates").mkdir(parents=True)
    big = "word " * 1200
    (refs / "templates/big.md").write_text("# T\n\n" + big, encoding="utf-8")
    (refs / "guide.md").write_text("# Ref\n\n[T](templates/big.md)\n", encoding="utf-8")
    assert checker.repository_findings(root) == []

    (refs / "guide.md").write_text("# Ref\n\n" + big + "\n[T](templates/big.md)\n", encoding="utf-8")
    assert any("references/guide.md: has 15" in f for f in checker.repository_findings(root))

    (refs / "guide.md").write_text("---\nname: guide\ndescription: Broken\n---\n# G\n", encoding="utf-8")
    skill.write_text(skill.read_text() + f"\n{checker.GUIDE_END}\n{checker.GUIDE_START}\n")
    assert any("malformed or inverted" in f for f in checker.repository_findings(root))
    seeded = skill.read_text().replace(
        f"{checker.GUIDE_END}\n{checker.GUIDE_START}",
        f"{checker.GUIDE_START}\n- [guide](references/guide.md): Broken\n{checker.GUIDE_END}",
    )
    skill.write_text(seeded, encoding="utf-8")
    (refs / "guide.md").write_text("---\nname: [unclosed\n---\n# G\n", encoding="utf-8")
    monkeypatch.setattr(checker, "ROOT", root)
    monkeypatch.setattr("sys.argv", ["skill_contracts", "--sync"])
    assert checker.main() == 1
    assert "invalid frontmatter" in capsys.readouterr().err
    assert skill.read_text(encoding="utf-8") == seeded

    (refs / "guide.md").write_text("---\nname: guide\ndescription: Sync.\n---\n# G\n", encoding="utf-8")
    (root / "skills/fixture-helper/SKILL.md").write_bytes(b"\xff\xfeinvalid")
    assert checker.main() == 1
    assert "cannot read UTF-8 text" in capsys.readouterr().err
    assert skill.read_text(encoding="utf-8") == seeded

    # Happy-path `--sync` rewrites a stale guide index and returns 0.
    _write_skill(root, name="fixture-helper")
    assert checker.main() == 0
    assert "- [guide](references/guide.md): Sync." in skill.read_text(encoding="utf-8")

    # Disconnected reference cycle stays orphaned and flagged as unreachable.
    (refs / "cycle_a.md").write_text("[B](cycle_b.md)\n", encoding="utf-8")
    (refs / "cycle_b.md").write_text("[A](cycle_a.md)\n", encoding="utf-8")
    cycle_findings = checker.repository_findings(root)
    assert any("cycle_a.md: resource is not reachable" in f for f in cycle_findings)
    assert any("cycle_b.md: resource is not reachable" in f for f in cycle_findings)


def test_skills_contract_rejects_stray_frontmatter_headings_supagents_and_script_hazards(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    sub_dir = root / "dot_agents/supagents"
    sub_dir.mkdir(parents=True)
    (sub_dir / "fmind-review-code.md").write_text("---\nname: fmind-review-code\ndescription: Review code.\n---\n# R\n")

    skill = root / "skills/fixture/SKILL.md"
    refs = skill.parent / "references"
    scripts = skill.parent / "scripts"
    scripts.mkdir()

    # Plain reference with stray frontmatter, manual ## Task guides, and unknown supagent ref.
    (refs / "guide.md").write_text(
        "---\ntitle: Stray\n---\n\n# Guide\n\n## Task guides\n\nRun `fmind-review-ghost` and `fmind-review-code`.\n",
        encoding="utf-8",
    )
    # Scripts with Python >3.10 syntax, unguarded suggest_on_error, and missing sys.dont_write_bytecode.
    (scripts / "helper.py").write_text("VALUE = 1\n", encoding="utf-8")
    (scripts / "tool.py").write_text(
        "import argparse\nimport helper\n"
        "def run():\n"
        "    try:\n"
        "        return argparse.ArgumentParser(suggest_on_error=True)\n"
        "    except ValueError, TypeError:\n"
        "        return helper.VALUE\n",
        encoding="utf-8",
    )
    skill.write_text(
        skill.read_text(encoding="utf-8") + "\nRun [tool](scripts/tool.py) with [helper](scripts/helper.py).\n",
        encoding="utf-8",
    )
    findings = checker.repository_findings(root)
    assert any("supporting reference must not include YAML frontmatter" in f for f in findings), findings
    assert any("reserve '## Task guides'" in f for f in findings), findings
    assert any("unknown reviewer supagent reference 'fmind-review-ghost'" in f for f in findings), findings
    assert not any("fmind-review-code" in f for f in findings), findings
    assert any("requires Python >3.10 syntax" in f for f in findings), findings

    # Fix syntax -> now unguarded suggest_on_error and missing dont_write_bytecode must fire.
    (scripts / "tool.py").write_text(
        "import argparse\nimport helper\n"
        "def run():\n"
        "    try:\n"
        "        return argparse.ArgumentParser(suggest_on_error=True)\n"
        "    except (ValueError, TypeError):\n"
        "        return helper.VALUE\n",
        encoding="utf-8",
    )
    findings2 = checker.repository_findings(root)
    assert any("avoid ArgumentParser(suggest_on_error=True)" in f for f in findings2), findings2
    assert any("sys.dont_write_bytecode = True" in f for f in findings2), findings2

    # Fix all issues -> zero findings.
    (refs / "guide.md").write_text("# Guide\n\n## References\n\nRun `fmind-review-code`.\n", encoding="utf-8")
    (scripts / "tool.py").write_text(
        "import argparse\nimport sys\nsys.dont_write_bytecode = True\nimport helper\n"
        "def run():\n"
        '    kw = {"suggest_on_error": True} if sys.version_info >= (3, 14) else {}\n'
        "    return argparse.ArgumentParser(**kw), helper.VALUE\n",
        encoding="utf-8",
    )
    assert checker.repository_findings(root) == []


def test_python_only_owned_sources_and_fzf_and_mise_locks(tmp_path: Path) -> None:
    owned = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, text=True, timeout=30
    ).splitlines()
    retired = {".go", ".js", ".jsx", ".ts", ".tsx"}
    active = {p for p in owned if Path(p).suffix in retired and (ROOT / p).exists()}
    assert active == set()

    for fetched in (False, True):
        home = tmp_path / str(fetched)
        theme = home / ".config/fzf/theme.conf"
        if fetched:
            theme.parent.mkdir(parents=True)
            theme.touch()
        env = {k: v for k, v in os.environ.items() if k != "FZF_DEFAULT_OPTS_FILE"} | {"HOME": str(home)}
        res = subprocess.run(
            [
                "fish",
                "--no-config",
                "-c",
                "source $argv[1]; set -q FZF_DEFAULT_OPTS_FILE; and echo $FZF_DEFAULT_OPTS_FILE",
                ROOT / "dot_config/fish/conf.d/fzf.fish",
            ],
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        assert res.stdout.strip() == (str(theme) if fetched else "")

    validate(ROOT, "mise.toml")
    validate(ROOT / "dot_config/mise", "config.toml")


def test_age_sources_encrypted_and_ignored_without_key(tmp_path: Path) -> None:
    headers = (b"-----BEGIN AGE ENCRYPTED FILE-----\n", b"age-encryption.org/v1\n")
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", "*.age"],
        cwd=ROOT,
        capture_output=True,
        check=True,
        timeout=30,
    ).stdout
    encrypted = [
        Path(n.decode())
        for n in listed.split(b"\0")
        if n and ((ROOT / n.decode()).exists() or (ROOT / n.decode()).is_symlink())
    ]
    assert encrypted
    for p in encrypted:
        assert not (ROOT / p).is_symlink()
        with (ROOT / p).open("rb") as f:
            assert f.read(64).startswith(headers), p

    source = tmp_path / "source"
    shutil.copytree(ROOT / ".chezmoitemplates", source / ".chezmoitemplates")
    shutil.copy2(ROOT / ".chezmoiignore", source / ".chezmoiignore")
    for rel in encrypted:
        (source / rel).parent.mkdir(parents=True, exist_ok=True)
        (source / rel).touch()
    pats = [
        ln.strip() for ln in chezmoi(source, "execute-template", "--file", str(source / ".chezmoiignore")).splitlines()
    ]
    pats = [p for p in pats if p and not p.startswith(("#", "!"))]
    for target in chezmoi(source, "target-path", *(str(source / rel) for rel in encrypted)).splitlines():
        rel_t = Path(target).relative_to(tmp_path).as_posix().removesuffix(".age")
        assert any(rel_t == pat or rel_t.startswith(f"{pat}/") or fnmatch.fnmatchcase(rel_t, pat) for pat in pats), (
            rel_t
        )


@pytest.mark.parametrize(
    ("template", "expected"),
    [
        ("Name <{}>", "alice"),
        ("mailto:{}", "alice"),
        ("https://host/{}", "alice"),
        ("\\n{}", "alice"),
        ("x\\{}", None),
        ("bob.{}", "bob.alice"),
    ],
)
def test_email_pattern_delimiters(template: str, expected: str | None) -> None:
    dom = ".".join(("corp", "io"))
    m = privacy.EMAIL_PATTERN.search(template.format(f"alice@{dom}"))
    assert (m.group(1) if m else None) == (f"{expected}@{dom}" if expected else None)


@pytest.mark.real_home
def test_repository_privacy_contracts() -> None:
    assert privacy.privacy_findings(ROOT) == []


def test_privacy_findings_and_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo, home = tmp_path / "repo", tmp_path / "home"
    repo.mkdir()
    (home / ".config/git").mkdir(parents=True)
    (home / ".config/dot.yaml").write_text(
        "auth:\n  workspace:\n    project: fmind-internal-9999\npull:\n  directories:\n    - ~/code/acme-internal/\ntrust:\n  github_owners:\n    - acme-corp\n"
    )
    bad_work, bad_peer = "@".join(("alice", "acmecorp.net")), "@".join(("bob", "corp-domain.io"))
    (home / ".config/git/config.acmecorp").write_text(f"[user]\n\temail = {bad_work}\n\tuser = alice-partner\n")
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True, timeout=30)
    (repo / "sample.py").write_text('SEND_AS = "github@fmind.dev"\nSA = "bot@example.iam.gserviceaccount.com"\n')
    subprocess.run(["git", "-C", str(repo), "add", "sample.py"], check=True, timeout=30)
    env = (
        os.environ
        | dict.fromkeys(("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL"), "github@fmind.dev")
        | {"GIT_AUTHOR_NAME": "F", "GIT_COMMITTER_NAME": "F"}
    )
    subprocess.run(
        ["git", "-C", str(repo), "-c", "commit.gpgsign=false", "commit", "-q", "-m", "ok"],
        env=env,
        check=True,
        timeout=30,
    )
    assert privacy.privacy_findings(repo, home=home) == []

    (repo / "sample.py").write_text(f'BAD = "{bad_peer}"\nPROJ = "fmind-internal-9999"\n')
    findings = privacy.privacy_findings(repo, home=home)
    assert any("unapproved email domain 'corp-domain.io'" in f for f in findings)
    assert any("local workstation identifier 'fmind-internal-9999'" in f for f in findings)
    (repo / "sample.py").write_text('OK = "alice@example.com"\n')
    (repo / "valid.age").write_bytes(b"-----BEGIN AGE ENCRYPTED FILE-----\nabc\n")
    assert privacy.privacy_findings(repo, home=home) == []
    (repo / "plain.age").write_text("SECRET=plaintext\n", encoding="utf-8")
    (repo / "link.age").symlink_to(repo / "valid.age")
    age_findings = privacy.privacy_findings(repo, home=home)
    assert any("plain.age: .age source is not age-encrypted ciphertext" in f for f in age_findings)
    assert any("link.age: encrypted .age source must not be a symlink" in f for f in age_findings)
    (repo / "plain.age").unlink()
    (repo / "link.age").unlink()
    (repo / "valid.age").unlink()
    subprocess.run(["git", "-C", str(repo), "add", "sample.py"], check=True, timeout=30)
    subprocess.run(
        ["git", "-C", str(repo), "-c", "commit.gpgsign=false", "commit", "-q", "-m", "bad"],
        env=env | {"GIT_AUTHOR_EMAIL": bad_work},
        check=True,
        timeout=30,
    )
    assert any(f"unapproved author email {bad_work!r}" in f for f in privacy.privacy_findings(repo, home=home))

    (home / ".config/git/config.acmecorp").unlink()
    monkeypatch.setattr(privacy.socket, "gethostname", lambda: "workbench.example.test")
    (home / ".config/dot.yaml").write_text(
        "trust:\n  github_owners: [acme-corp]\nprivacy:\n  allowed_tokens: [WorkBench]\n"
    )
    (home / ".config/dot.work.yaml").write_text("pull:\n  directories: [~/work/secondary-org]\n")
    assert privacy._workstation_tokens(home, include_hostname=True) == {"acme-corp", "secondary-org"}


@pytest.mark.parametrize(
    "payload",
    [b"trust:\n  github_owners: [secret-corp-token\n", b"\xff\xfe", b"[" * 1200 + b"]" * 1200, b"- not-map\n"],
)
def test_privacy_invalid_configs_and_ssh_comments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: bytes
) -> None:
    repo, home = tmp_path / "repo", tmp_path / "home"
    repo.mkdir()
    (home / ".config/git").mkdir(parents=True)
    (repo / "sample.py").write_text('OK = "alice@example.com"\n')
    (home / ".config/dot.yaml").write_bytes(payload)
    findings = privacy.privacy_findings(repo, home=home)
    assert len(findings) == 1
    assert "cannot load local privacy tokens" in findings[0]
    assert "secret-corp-token" not in findings[0]

    (home / ".config/dot.yaml").unlink()
    (home / ".config/git/config.work").write_bytes(b"\xff\xfe")
    assert any("config.work: cannot load local privacy tokens" in f for f in privacy.privacy_findings(repo, home=home))
    (home / ".config/git/config.work").unlink()

    ed, rsa = "ssh-ed25519", "ssh-rsa"
    (repo / "allowed_signers").write_text(f"{ed} AAAA git-signing@fmind.dev\n{ed} AAAA fmind@studio\n{rsa} AAAA= box\n")
    assert [f.split(" may ")[0] for f in privacy.privacy_findings(repo, home=home)] == [
        "allowed_signers: SSH key comment 'box'",
        "allowed_signers: SSH key comment 'fmind@studio'",
    ]

    override = tmp_path / "dot.custom.yaml"
    override.write_text("trust:\n  github_owners: [custom-org-99]\n")
    linked = tmp_path / "linked-home"
    linked.symlink_to(home, target_is_directory=True)
    (repo / "allowed_signers").unlink()
    (repo / "sample.py").write_text('LEAK = "custom-org-99"\n')
    monkeypatch.setenv("HOME", str(linked))
    monkeypatch.setenv("DOT_CONFIG_PATH", str(override))
    assert any(
        "local workstation identifier 'custom-org-99'" in f
        for f in privacy.privacy_findings(repo, include_hostname=False)
    )
