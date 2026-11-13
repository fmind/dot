# Settings Baseline

Apply to new solo-maintained repositories or explicit settings passes; preserve team policies and active wiki/projects/discussions unless removal is requested. [settings_baseline.py](../scripts/settings_baseline.py) defaults to a GET-only check and applies settings idempotently only when `--apply` is passed.

## Workflow

1. **Select flags**:
   - `--disable wiki --disable projects --disable discussions` on new repos (on existing repos, pass only features requested for removal; add `--disable issues` only when tracked externally).
   - `--skip-sha-pinning` while `.github/workflows` or `.github/actions` has unpinned `uses:` ([jactionlint](../../../../github-actions/references/jactionlint.md) `unpinned-uses`); GitHub-managed workflows (CodeQL, Dependabot, dependency graph, legacy Pages) work regardless.
1. **Preview** (default GET-only check; `--check` is an explicit alias):

   ```bash
   python3 -I ~/.agents/skills/gh/references/repository/scripts/settings_baseline.py OWNER/REPO
   ```

1. **Apply** (requires explicit `--apply`; aborts on failed reads or duplicate rulesets):

   ```bash
   python3 -I ~/.agents/skills/gh/references/repository/scripts/settings_baseline.py OWNER/REPO --apply --disable wiki --disable projects --disable discussions
   ```

1. **Verify JSON output**: `state`, `changed` (`[before, after]`), `notes`, and `drift` (exit `0` clean, `1` failed/drift, `2` bad args). Pass identical flags on follow-ups.

## Decisions

| Setting                                                                        | Applied when                                                               |
| ------------------------------------------------------------------------------ | -------------------------------------------------------------------------- |
| Squash-only merges (`PR_TITLE` + `PR_BODY`), auto-delete branches, branch sync | Always                                                                     |
| Secret scanning & push protection                                              | Public, or `secret_scanning` enabled; else noted                           |
| Dependabot alerts & security updates                                           | Always ([dependabot](../../../../github-actions/references/dependabot.md)) |
| Full-SHA pins, read-only `GITHUB_TOKEN`, no Actions PR approvals               | Actions enabled                                                            |
| Outside-contributor fork PR approval required                                  | Public with Actions enabled                                                |
| Immutable releases; `pypi`/`release` environments restricted to `v*`           | Public with release or env                                                 |
| Private vulnerability reporting; `Protect default branch` ruleset              | Public                                                                     |

- **Upload release assets before publishing**: immutable releases freeze tags/assets on publish; rerun baseline after a new repo's first release.
- **Preserve reviewers & extra deploy policies**: `PUT` carries forward reviewers/`prevent_self_review`/`wait_timer`; extra policies surface in `drift` with `DELETE` paths for user approval.
- **Keep direct pushes working**: `Protect default branch` blocks deletion/force-pushes without requiring PRs or signatures; duplicate owned rulesets abort with IDs for user cleanup.

## Gotchas

- **Capability-detect secret scanning**: public repos include it; private/internal repos require Secret Protection or Advanced Security regardless of user vs org ownership.
- **Report Free-plan limits without changing visibility**: private rulesets/branch protection return 403 `Upgrade to GitHub Pro` on Free, and private vulnerability reporting is public-only; report skipped items as notes.
- **Never edit organization rulesets**: `rules/branches/<branch>` merges org and repo rules; mutate only the repo's owned ruleset.
- **Do not retry paid secret-scanning subfeatures**: validity checks and non-provider patterns stay `disabled` silently on Free.
- **Check owner-level `SECURITY.md`**: public `<owner>/.github` (`gh api repos/<owner>/.github/contents/SECURITY.md`; `fmind/.github` routes to private vulnerability reporting) covers public repos unless repo-specific scope/versions need a local `SECURITY.md`.
- **Personal repos have no read-only collaborator role**: downgrading to `pull` returns 422 on user-owned repos (remove inactive collaborators instead; orgs support `pull`).
- **Harden organizations once**: enforce 2FA (web UI), SHA-pinned actions, and default "GitHub recommended" code security with temporary `admin:org` (`dot login github --grant admin:org`, then `dot setup github`).

## Documentation

- [Repository rulesets API](https://docs.github.com/en/rest/repos/rules) · [Dependabot security updates API](https://docs.github.com/en/rest/repos/repos#enable-dependabot-security-updates) · [Private vulnerability reporting API](https://docs.github.com/en/rest/repos/repos#enable-private-vulnerability-reporting-for-a-repository)
- [Actions permissions API](https://docs.github.com/en/rest/actions/permissions) · [Immutable releases](https://docs.github.com/en/code-security/supply-chain-security/understanding-your-software-supply-chain/immutable-releases) · [Default community health files](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)
