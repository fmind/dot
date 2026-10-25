"""Run the GitHub settings baseline script against a fake gh that records every call."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/github-repository/scripts/settings_baseline.py"
BASE = "repos/owner/repo"
# Canned GET responses keyed by "GET path"; an unlisted GET answers 404 like a disabled feature.
# The read-back starts with the first repository GET after a mutation; from then on "after" overrides "before".
FAKE_GH = """
import json, os, sys
from pathlib import Path
log = Path(os.environ["FAKE_GH_LOG"])
args = sys.argv[1:]
body = sys.stdin.read() if "--input" in args else ""
with log.open("a") as stream:
    stream.write(json.dumps({"args": args, "body": json.loads(body) if body else None}) + "\\n")
if args[0] != "api" or args[2] != "GET":
    sys.exit(0)
mutated = after = False
for line in log.read_text().splitlines():
    call = json.loads(line)["args"]
    if call[0] != "api" or call[2] != "GET":
        mutated = True
    elif mutated and call[-1] == "repos/owner/repo":
        after = True
scenario = json.loads(Path(os.environ["FAKE_GH_SCENARIO"]).read_text())
responses = {**scenario["before"], **(scenario.get("after", {}) if after else {})}
if f"GET {args[-1]}" not in responses:
    sys.stderr.write("gh: Not Found (HTTP 404)\\n")
    sys.exit(1)
print(json.dumps(responses[f"GET {args[-1]}"]))
"""
MERGED = {
    "delete_branch_on_merge": True,
    "allow_squash_merge": True,
    "allow_merge_commit": False,
    "allow_rebase_merge": False,
    "allow_update_branch": True,
    "squash_merge_commit_title": "PR_TITLE",
    "squash_merge_commit_message": "PR_BODY",
}
REVIEWERS = {
    "type": "required_reviewers",
    "prevent_self_review": True,
    "reviewers": [{"type": "User", "reviewer": {"id": 7, "login": "owner"}}],
}


def repository(visibility: str, **fields: Any) -> dict[str, Any]:
    return {"visibility": visibility, "default_branch": "main", "security_and_analysis": {}, **fields}


def public_before(rulesets: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        f"GET {BASE}": repository("public", allow_merge_commit=True),
        f"GET {BASE}/actions/permissions": {
            "enabled": True,
            "allowed_actions": "selected",
            "sha_pinning_required": False,
        },
        f"GET {BASE}/actions/permissions/workflow": {
            "default_workflow_permissions": "write",
            "can_approve_pull_request_reviews": True,
        },
        f"GET {BASE}/actions/permissions/fork-pr-contributor-approval": {"approval_policy": "first_time_contributors"},
        f"GET {BASE}/environments?per_page=100": [
            {
                "environments": [
                    {"name": "pypi", "protection_rules": [{"type": "wait_timer", "wait_timer": 5}, REVIEWERS]},
                    {"name": "docs"},
                ]
            }
        ],
        f"GET {BASE}/releases?per_page=1": [{"id": 1}],
        f"GET {BASE}/private-vulnerability-reporting": {"enabled": False},
        f"GET {BASE}/rulesets?includes_parents=false&per_page=100": [rulesets or []],
        f"GET {BASE}/rules/branches/main?per_page=100": [[]],
        f"GET {BASE}/environments/pypi/deployment-branch-policies?per_page=100": [{"branch_policies": []}],
    }


def public_after() -> dict[str, Any]:
    pypi = {"name": "pypi", "deployment_branch_policy": {"protected_branches": False, "custom_branch_policies": True}}
    return {
        f"GET {BASE}": repository(
            "public",
            **MERGED,
            has_wiki=False,
            security_and_analysis={
                "secret_scanning": {"status": "enabled"},
                "secret_scanning_push_protection": {"status": "enabled"},
            },
        ),
        f"GET {BASE}/automated-security-fixes": {"enabled": True, "paused": False},
        f"GET {BASE}/actions/permissions": {
            "enabled": True,
            "allowed_actions": "selected",
            "sha_pinning_required": True,
        },
        f"GET {BASE}/actions/permissions/workflow": {
            "default_workflow_permissions": "read",
            "can_approve_pull_request_reviews": False,
        },
        f"GET {BASE}/actions/permissions/fork-pr-contributor-approval": {
            "approval_policy": "all_external_contributors"
        },
        f"GET {BASE}/environments?per_page=100": [{"environments": [pypi]}],
        f"GET {BASE}/immutable-releases": {"enabled": True, "enforced_by_owner": False},
        f"GET {BASE}/private-vulnerability-reporting": {"enabled": True},
        f"GET {BASE}/rulesets?includes_parents=false&per_page=100": [
            [{"id": 3, "name": "Protect default branch", "enforcement": "active"}]
        ],
        f"GET {BASE}/rules/branches/main?per_page=100": [[{"type": "deletion"}, {"type": "non_fast_forward"}]],
        f"GET {BASE}/environments/pypi/deployment-branch-policies?per_page=100": [
            {"branch_policies": [{"name": "v*", "type": "tag"}]}
        ],
    }


def run(
    tmp_path: Path, scenario: dict[str, Any], *args: str, repo: str = "owner/repo"
) -> tuple[subprocess.CompletedProcess[str], list[dict[str, Any]]]:
    gh = tmp_path / "gh"
    gh.write_text(f"#!{sys.executable}\n{FAKE_GH}", encoding="utf-8")
    gh.chmod(0o700)
    (tmp_path / "scenario.json").write_text(json.dumps(scenario), encoding="utf-8")
    log = tmp_path / "calls.jsonl"
    env = {
        **os.environ,
        "PATH": str(tmp_path),
        "FAKE_GH_LOG": str(log),
        "FAKE_GH_SCENARIO": str(tmp_path / "scenario.json"),
    }
    result = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), repo, *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=120,
    )
    calls = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []
    return result, calls


def mutations(calls: list[dict[str, Any]]) -> list[tuple[str, ...]]:
    found: list[tuple[str, ...]] = []
    for call in calls:
        args = call["args"]
        if args[:2] == ["repo", "edit"]:
            found.append(tuple(args))
        elif args[2] != "GET":
            found.append((args[2], args[-1]))
    return found


def bodies(calls: list[dict[str, Any]]) -> dict[str, Any]:
    return {call["args"][-1]: call["body"] for call in calls if call["body"] is not None}


def test_public_apply_sets_every_baseline_setting(tmp_path: Path) -> None:
    result, calls = run(tmp_path, {"before": public_before(), "after": public_after()}, "--disable", "wiki")
    assert result.returncode == 0, result.stderr
    assert mutations(calls) == [
        (
            "repo",
            "edit",
            "owner/repo",
            "--delete-branch-on-merge",
            "--enable-squash-merge",
            "--squash-merge-commit-message",
            "pr-title-description",
            "--enable-merge-commit=false",
            "--enable-rebase-merge=false",
            "--allow-update-branch",
            "--enable-wiki=false",
            "--enable-secret-scanning",
            "--enable-secret-scanning-push-protection",
        ),
        ("PUT", f"{BASE}/vulnerability-alerts"),
        ("PUT", f"{BASE}/automated-security-fixes"),
        ("PUT", f"{BASE}/actions/permissions"),
        ("PUT", f"{BASE}/actions/permissions/workflow"),
        ("PUT", f"{BASE}/actions/permissions/fork-pr-contributor-approval"),
        ("PUT", f"{BASE}/immutable-releases"),
        ("PUT", f"{BASE}/environments/pypi"),
        ("POST", f"{BASE}/environments/pypi/deployment-branch-policies"),
        ("PUT", f"{BASE}/private-vulnerability-reporting"),
        ("POST", f"{BASE}/rulesets"),
    ]
    sent = bodies(calls)
    assert sent[f"{BASE}/actions/permissions"] == {
        "enabled": True,
        "allowed_actions": "selected",
        "sha_pinning_required": True,
    }
    assert sent[f"{BASE}/environments/pypi"] == {
        "wait_timer": 5,
        "prevent_self_review": True,
        "reviewers": [{"type": "User", "id": 7}],
        "deployment_branch_policy": {"protected_branches": False, "custom_branch_policies": True},
    }
    assert sent[f"{BASE}/environments/pypi/deployment-branch-policies"] == {"name": "v*", "type": "tag"}
    report = json.loads(result.stdout)
    assert report["drift"] == []
    assert report["changed"]["allow_merge_commit"] == [True, False]


def test_private_repository_without_secret_scanning_reports_the_gap(tmp_path: Path) -> None:
    before = {
        f"GET {BASE}": repository("private"),
        f"GET {BASE}/actions/permissions": {"enabled": False},
    }
    after = {f"GET {BASE}": repository("private", **MERGED), f"GET {BASE}/automated-security-fixes": {"enabled": True}}
    result, calls = run(tmp_path, {"before": before, "after": after})
    assert result.returncode == 0, result.stderr
    edit, *rest = mutations(calls)
    assert "--enable-secret-scanning" not in edit
    assert rest == [("PUT", f"{BASE}/vulnerability-alerts"), ("PUT", f"{BASE}/automated-security-fixes")]
    notes = json.loads(result.stdout)["notes"]
    assert any("secret scanning is unavailable" in note for note in notes)
    assert any("Actions is disabled" in note for note in notes)


def test_duplicate_rulesets_stop_before_any_change(tmp_path: Path) -> None:
    owned = [{"id": 7, "name": "Protect default branch"}, {"id": 9, "name": "Protect default branch"}]
    result, calls = run(tmp_path, {"before": public_before(owned)})
    assert result.returncode == 1
    assert "rulesets 7, 9" in result.stderr
    assert "nothing was changed" in result.stderr
    assert mutations(calls) == []


def test_check_only_reads_and_reports_drift(tmp_path: Path) -> None:
    result, calls = run(tmp_path, {"before": public_before()}, "--check")
    assert result.returncode == 1
    assert calls
    assert mutations(calls) == []
    drift = json.loads(result.stdout)["drift"]
    assert "allow_merge_commit: expected false, found true" in drift
    assert "automated_security_fixes: expected true, found false" in drift
    assert "default_branch_protected: expected true, found false" in drift


def test_invalid_repository_is_a_usage_error(tmp_path: Path) -> None:
    result, calls = run(tmp_path, {"before": {}}, "--check", repo="../escape")
    assert result.returncode == 2
    assert calls == []
