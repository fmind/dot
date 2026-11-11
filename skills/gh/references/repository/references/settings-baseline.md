# Settings Baseline

Apply to new solo-maintained repositories or explicit settings passes; preserve team policies and active wiki/projects/discussions unless removal is requested. [settings_baseline.py](../scripts/settings_baseline.py) defaults to a GET-only check and applies settings idempotently only when `--apply` is passed.

## Workflow

1. **Select flags**:
   - `--disable wiki --disable projects --disable discussions` on new repos (on existing repos, pass only features requested for removal; add `--disable issues` only when tracked externally).
   - `--skip-sha-pinning` while `.github/workflows` or `.github/actions` has unpinned `uses:` ([jactionlint](../../../../github-actions/references/jactionlint.md) `unpinned-uses`); GitHub-managed workflows (CodeQL, Dependabot, dependency graph, legacy Pages) work regardless.
1. **Preview** (default GET-only check; `--check` is an explicit alias):

   ```bash
   python -I ~/.agents/skills/gh/references/repository/scripts/settings_baseline.py OWNER/REPO
   ```

1. **Apply** (requires explicit `--apply`; stops before writes on failed reads or duplicate rulesets):

   ```bash
   python -I ~/.agents/skills/gh/references/repository/scripts/settings_baseline.py OWNER/REPO --apply --disable wiki --disable projects --disable discussions
   ```

1. **Verify JSON output**: `state`, `changed` (`[before, after]` on `--apply`), `notes`, and `drift` (exit `0` clean, `1` failed `gh`/duplicate rulesets/drift, `2` bad args). Pass identical flags on follow-up checks (rerun once if API propagation lags).

## Decisions

| Setting                                                                             | Applied when                                                                                  |
| ----------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Squash-only merges (`PR_TITLE` + `PR_BODY`), auto-delete head branches, branch sync | Always                                                                                        |
| Secret scanning and push protection                                                 | Public, or `security_and_analysis.secret_scanning` present; else noted                        |
| Dependabot alerts and security updates                                              | Always (free on all plans; [dependabot](../../../../github-actions/references/dependabot.md)) |
| Full-SHA action pins, read-only `GITHUB_TOKEN`, no PR approvals by Actions          | Actions enabled (writing `actions/permissions` when off would enable Actions)                 |
| Outside-contributor fork PR approval required                                       | Public with Actions enabled                                                                   |
| Immutable releases; `pypi` and `release` environments restricted to `v*` tags       | Public with an existing release or `pypi`/`release` environment                               |
| Private vulnerability reporting; `Protect default branch` ruleset                   | Public                                                                                        |

- **Upload release assets before publishing**: immutable releases freeze tags/assets on publish and attach release attestations (`gh release create` with assets, or publish drafts last). Rerun the baseline after a new repo's first release.
- **Preserve environment reviewers**: environment `PUT` replaces settings, so the script carries forward reviewers, `prevent_self_review`, and `wait_timer`.
- **Never auto-delete extra deployment policies**: leftover branch/tag policies on `pypi`/`release` still permit deploys; the script flags them in `drift` with `gh api --method DELETE` paths for user-approved removal.
- **Keep direct pushes working**: `Protect default branch` blocks deletion and force-pushes without requiring PRs or signatures, updating in place or skipping creation if another ruleset enforces both; duplicate owned rulesets abort with IDs for user-approved cleanup.

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
