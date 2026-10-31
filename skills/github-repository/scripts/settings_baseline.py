"""Apply or check the solo-maintainer GitHub settings baseline for one repository through gh."""

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass

type Record = dict[str, object]

TIMEOUT = 120
FEATURES = ("issues", "wiki", "projects", "discussions")
PUBLISHING_ENVIRONMENTS = ("pypi", "release")
RELEASE_TAGS = "v*"
RULESET_NAME = "Protect default branch"
# Blocks deletion and force pushes without requiring pull requests or signatures, so direct pushes keep working.
RULESET: Record = {
    "name": RULESET_NAME,
    "target": "branch",
    "enforcement": "active",
    "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
    "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}],
    "bypass_actors": [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}],
}
MERGE_FLAGS = (
    "--delete-branch-on-merge",
    "--enable-squash-merge",
    "--squash-merge-commit-message",
    "pr-title-description",
    "--enable-merge-commit=false",
    "--enable-rebase-merge=false",
    "--allow-update-branch",
)
MERGE_POLICY: Record = {
    "delete_branch_on_merge": True,
    "allow_squash_merge": True,
    "allow_merge_commit": False,
    "allow_rebase_merge": False,
    "allow_update_branch": True,
    "squash_merge_commit_title": "PR_TITLE",
    "squash_merge_commit_message": "PR_BODY",
}
REPOSITORY = re.compile(r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+")


class BaselineError(Exception):
    """A failed gh call or an unsafe state that must stop the run."""


class NotFoundError(BaselineError):
    """gh answered HTTP 404."""


def gh(*args: str, body: object = None) -> str:
    """Run gh without a shell or prompts; a failure keeps gh's own error text."""
    executable = shutil.which("gh")
    if executable is None:
        raise BaselineError("gh is not on PATH; install it and run `gh auth login`.")
    command = [executable, *args]
    shown = shlex.join(["gh", *args])
    try:
        result = subprocess.run(  # noqa: S603 - fixed gh executable; arguments are a list, bodies go through stdin
            command,
            input="" if body is None else json.dumps(body),
            capture_output=True,
            text=True,
            env={**os.environ, "GH_PROMPT_DISABLED": "1"},
            timeout=TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise BaselineError(f"{shown}: timed out after {TIMEOUT} s") from error
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit status {result.returncode}"
        error_type = NotFoundError if "(HTTP 404)" in result.stderr else BaselineError
        raise error_type(f"{shown}: {detail}")
    return result.stdout


def get(path: str, *, paginate: bool = False) -> object:
    pages = ("--paginate", "--slurp") if paginate else ()
    output = gh("api", "--method", "GET", *pages, path)
    try:
        return json.loads(output)
    except json.JSONDecodeError as error:
        raise BaselineError(f"GET {path}: gh returned invalid JSON") from error


def record(value: object, where: str) -> Record:
    if not isinstance(value, dict):
        raise BaselineError(f"{where}: expected a JSON object")
    return value


def records(value: object, where: str) -> list[Record]:
    if not isinstance(value, list):
        raise BaselineError(f"{where}: expected a JSON array")
    return [record(item, where) for item in value]


def get_record(path: str) -> Record:
    return record(get(path), path)


def get_all(path: str, key: str | None = None) -> list[Record]:
    """Read every page (`--slurp` wraps them in one array); `key` selects the items inside object pages."""
    pages = get(path, paginate=True)
    if not isinstance(pages, list):
        raise BaselineError(f"{path}: expected a JSON array of pages")
    items: list[Record] = []
    for page in pages:
        items.extend(records(record(page, path).get(key) or [], path) if key else records(page, path))
    return items


def enabled(path: str) -> bool:
    """Read an endpoint that answers 404 while its feature is off."""
    try:
        return get_record(path).get("enabled") is True
    except NotFoundError:
        return False


def write(method: str, path: str, body: Record | None = None) -> None:
    sys.stderr.write(f"{method} {path}\n")
    gh("api", "--method", method, *(("--input", "-") if body is not None else ()), path, body=body)


@dataclass(frozen=True)
class State:
    """Repository facts that drive the decisions, plus the flat read-back that is printed and compared."""

    repository: str
    public: bool
    secret_scanning: bool
    actions: Record
    environments: dict[str, Record]
    publishes: bool
    owned_rulesets: list[object]
    report: Record


def tag_policies(base: str, environment: str) -> set[object]:
    path = f"{base}/environments/{environment}/deployment-branch-policies?per_page=100"
    return {item.get("name") for item in get_all(path, "branch_policies") if item.get("type") == "tag"}


def release_tags_only(base: str, name: str, environment: Record) -> bool:
    policy = environment.get("deployment_branch_policy")
    if not isinstance(policy, dict) or policy.get("custom_branch_policies") is not True:
        return False
    return RELEASE_TAGS in tag_policies(base, name)


def inspect(repository: str) -> State:
    """Read everything with GET requests only; any failed read stops the run before a decision depends on it."""
    base = f"repos/{repository}"
    repo = get_record(base)
    public = repo.get("visibility") == "public"
    raw_analysis = repo.get("security_and_analysis")
    analysis: Record = raw_analysis if isinstance(raw_analysis, dict) else {}

    def status(name: str) -> object:
        value = analysis.get(name)
        return value.get("status") if isinstance(value, dict) else None

    report: Record = {
        "visibility": repo.get("visibility"),
        "default_branch": repo.get("default_branch"),
        **{key: repo.get(key) for key in MERGE_POLICY},
        **{f"has_{feature}": repo.get(f"has_{feature}") for feature in FEATURES},
        "secret_scanning": status("secret_scanning"),
        "secret_scanning_push_protection": status("secret_scanning_push_protection"),
        "automated_security_fixes": enabled(f"{base}/automated-security-fixes"),
    }
    actions = get_record(f"{base}/actions/permissions")
    report |= {
        "actions_enabled": actions.get("enabled"),
        "allowed_actions": actions.get("allowed_actions"),
        "sha_pinning_required": actions.get("sha_pinning_required"),
    }
    if actions.get("enabled") is True:
        workflow = get_record(f"{base}/actions/permissions/workflow")
        report |= {
            key: workflow.get(key) for key in ("default_workflow_permissions", "can_approve_pull_request_reviews")
        }
        if public:
            approval = get_record(f"{base}/actions/permissions/fork-pr-contributor-approval")
            report["fork_pr_approval_policy"] = approval.get("approval_policy")
    environments: dict[str, Record] = {}
    owned: list[object] = []
    publishes = False
    if public:
        environments = {
            str(item.get("name")): item
            for item in get_all(f"{base}/environments?per_page=100", "environments")
            if item.get("name") in PUBLISHING_ENVIRONMENTS
        }
        report["releases"] = bool(records(get(f"{base}/releases?per_page=1"), "releases"))
        # A published release or a publishing environment shows the repository ships GitHub releases.
        publishes = report["releases"] is True or bool(environments)
        report["immutable_releases"] = enabled(f"{base}/immutable-releases")
        for name, environment in environments.items():
            report[f"environment.{name}.release_tags_only"] = release_tags_only(base, name, environment)
        report["private_vulnerability_reporting"] = get_record(f"{base}/private-vulnerability-reporting").get("enabled")
        rulesets = get_all(f"{base}/rulesets?includes_parents=false&per_page=100")
        owned = [item.get("id") for item in rulesets if item.get("name") == RULESET_NAME]
        if not all(isinstance(item, int) for item in owned):
            raise BaselineError(f"{base}/rulesets: unexpected ruleset id")
        report["rulesets"] = [{key: item.get(key) for key in ("id", "name", "enforcement")} for item in rulesets]
        branch = repo.get("default_branch")
        if not isinstance(branch, str) or not branch:
            raise BaselineError(f"{base}: missing default_branch")
        # Effective rules merge organization and repository rulesets.
        rules = get_all(f"{base}/rules/branches/{branch}?per_page=100")
        report["default_branch_protected"] = {"deletion", "non_fast_forward"} <= {rule.get("type") for rule in rules}
    return State(
        repository=repository,
        public=public,
        secret_scanning=public or bool(status("secret_scanning")),
        actions=actions,
        environments=environments,
        publishes=publishes,
        owned_rulesets=owned,
        report=report,
    )


def environment_body(name: str, environment: Record) -> Record:
    """PUT replaces an environment's settings, so carry its reviewers and wait timer forward."""
    rules = records(environment.get("protection_rules") or [], name)
    timers = [rule.get("wait_timer") for rule in rules if rule.get("type") == "wait_timer"]
    reviewer_rules = [rule for rule in rules if rule.get("type") == "required_reviewers"]
    reviewers: list[Record] = []
    for rule in reviewer_rules:
        for item in records(rule.get("reviewers") or [], name):
            reviewer = record(item.get("reviewer"), name)
            if item.get("type") not in {"User", "Team"} or not isinstance(reviewer.get("id"), int):
                raise BaselineError(f"environment {name}: unexpected reviewer shape; refusing to drop it")
            reviewers.append({"type": item["type"], "id": reviewer["id"]})
    return {
        "wait_timer": (timers[0] if timers else None) or 0,
        "prevent_self_review": (reviewer_rules[0].get("prevent_self_review") if reviewer_rules else None) or False,
        "can_admins_bypass": True,
        "reviewers": reviewers or None,
        "deployment_branch_policy": {"protected_branches": False, "custom_branch_policies": True},
    }


def duplicates(state: State) -> str | None:
    if len(state.owned_rulesets) < 2:
        return None
    ids = ", ".join(str(item) for item in state.owned_rulesets)
    return f"duplicate {RULESET_NAME!r} rulesets {ids}: delete extras only with the user's approval, then rerun"


def apply(state: State, args: argparse.Namespace) -> None:
    """Change only what the baseline owns; every call is idempotent."""
    problem = duplicates(state)
    if problem:
        raise BaselineError(f"{problem}; nothing was changed")
    base = f"repos/{state.repository}"
    flags = [*MERGE_FLAGS, *(f"--enable-{feature}=false" for feature in args.disable)]
    if state.secret_scanning:
        flags += ["--enable-secret-scanning", "--enable-secret-scanning-push-protection"]
    sys.stderr.write(shlex.join(["gh", "repo", "edit", state.repository, *flags]) + "\n")
    gh("repo", "edit", state.repository, *flags)
    write("PUT", f"{base}/vulnerability-alerts")
    write("PUT", f"{base}/automated-security-fixes")
    # Only touch Actions when it is on: this endpoint's `enabled` field would switch it on.
    if state.actions.get("enabled") is True:
        if not args.skip_sha_pinning:
            body: Record = {"enabled": True, "allowed_actions": state.actions.get("allowed_actions")}
            body = {key: value for key, value in body.items() if value is not None} | {"sha_pinning_required": True}
            write("PUT", f"{base}/actions/permissions", body)
        workflow: Record = {"default_workflow_permissions": "read", "can_approve_pull_request_reviews": False}
        write("PUT", f"{base}/actions/permissions/workflow", workflow)
        if state.public:
            approval: Record = {"approval_policy": "all_external_contributors"}
            write("PUT", f"{base}/actions/permissions/fork-pr-contributor-approval", approval)
    if state.public and state.publishes:
        write("PUT", f"{base}/immutable-releases")
        for name, environment in state.environments.items():
            path = f"{base}/environments/{name}"
            write("PUT", path, environment_body(name, environment))
            if RELEASE_TAGS not in tag_policies(base, name):
                write("POST", f"{path}/deployment-branch-policies", {"name": RELEASE_TAGS, "type": "tag"})
    if state.public:
        write("PUT", f"{base}/private-vulnerability-reporting")  # the owner's .github SECURITY.md points here
        if state.owned_rulesets:
            write("PUT", f"{base}/rulesets/{state.owned_rulesets[0]}", RULESET)
        elif state.report.get("default_branch_protected") is not True:  # read succeeded, or inspect() stopped
            write("POST", f"{base}/rulesets", RULESET)


def expectations(state: State, args: argparse.Namespace) -> tuple[Record, list[str]]:
    """Return the expected read-back values and notes about settings left unchanged."""
    expected: Record = {**MERGE_POLICY, **{f"has_{feature}": False for feature in args.disable}}
    notes: list[str] = []
    if state.secret_scanning:
        expected |= {"secret_scanning": "enabled", "secret_scanning_push_protection": "enabled"}
    else:
        notes.append("secret scanning is unavailable (no security_and_analysis.secret_scanning); left unchanged")
    expected["automated_security_fixes"] = True
    if state.actions.get("enabled") is True:
        if not args.skip_sha_pinning:
            expected["sha_pinning_required"] = True
        expected |= {"default_workflow_permissions": "read", "can_approve_pull_request_reviews": False}
        if state.public:
            expected["fork_pr_approval_policy"] = "all_external_contributors"
    else:
        notes.append("GitHub Actions is disabled; Actions hardening left untouched")
    if not state.public:
        notes.append("private repository: fork PR approval, releases, vulnerability reporting, and rulesets skipped")
        return expected, notes
    if state.publishes:
        expected["immutable_releases"] = True
        expected |= {f"environment.{name}.release_tags_only": True for name in state.environments}
    else:
        notes.append("no GitHub release or pypi/release environment yet; immutable releases skipped")
    expected |= {"private_vulnerability_reporting": True, "default_branch_protected": True}
    if not state.owned_rulesets and state.report.get("default_branch_protected") is True:
        notes.append("another ruleset already blocks deletion and force pushes on the default branch")
    return expected, notes


def repository_name(value: str) -> str:
    if not REPOSITORY.fullmatch(value):
        raise argparse.ArgumentTypeError(f"expected OWNER/REPO, got {value!r}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", metavar="OWNER/REPO", type=repository_name)
    parser.add_argument("--check", action="store_true", help="only read back and compare (GET requests only)")
    parser.add_argument(
        "--disable", action="append", default=[], choices=FEATURES, help="turn a sidebar feature off (repeatable)"
    )
    parser.add_argument(
        "--skip-sha-pinning",
        action="store_true",
        help="leave the SHA-pin requirement as is while any uses: is unpinned",
    )
    args = parser.parse_args()
    try:
        before = after = inspect(args.repository)
        if not args.check:
            apply(before, args)
            after = inspect(args.repository)
    except BaselineError as error:
        sys.stderr.write(f"error: {error}\n")
        return 1
    expected, notes = expectations(after, args)
    found = after.report
    drift = [
        f"{key}: expected {json.dumps(value)}, found {json.dumps(found.get(key))}"
        for key, value in expected.items()
        if found.get(key) != value
    ]
    problem = duplicates(after)
    if problem:
        drift.append(problem)
    result: Record = {"repository": args.repository, "state": found, "notes": notes, "drift": drift}
    if not args.check:
        result["changed"] = {
            key: [before.report.get(key), value] for key, value in found.items() if before.report.get(key) != value
        }
    sys.stdout.write(json.dumps(result, indent=2) + "\n")
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
