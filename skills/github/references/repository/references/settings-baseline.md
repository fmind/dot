# Settings Baseline

Apply to new solo-maintained `github.com` repos or explicit settings passes; preserve team policies and active wiki/projects/discussions unless removal is requested. [settings_baseline.py](../scripts/settings_baseline.py) defaults to a GET-only check and writes idempotently only with `--apply`.

## Workflow

1. **Select flags**: `--disable wiki --disable projects --disable discussions` on new repos (on existing repos, pass only requested removals; `--disable issues` only if tracked externally); `--skip-sha-pinning` while workflows/actions have unpinned `uses:` ([jactionlint](../../jactionlint.md)).
1. **Preview (`GET`-only) or apply (`--apply`)** (aborts on failed reads or duplicate rulesets; verify `state`, `changed`, `notes`, `drift` JSON):

   ```bash
   python3 -I ~/.agents/skills/github/references/repository/scripts/settings_baseline.py OWNER/REPO
   python3 -I ~/.agents/skills/github/references/repository/scripts/settings_baseline.py OWNER/REPO --apply --disable wiki --disable projects --disable discussions
   ```

## Decisions

| Setting                                                               | Applied when                                       |
| --------------------------------------------------------------------- | -------------------------------------------------- |
| Squash-only (`PR_TITLE`+`PR_BODY`), auto-delete branches, branch sync | Always                                             |
| Secret scanning & push protection                                     | Public, or `secret_scanning` available; else noted |
| Dependabot alerts & security updates                                  | Always ([dependabot](../../dependabot.md))         |
| Full-SHA pins, read-only `GITHUB_TOKEN`, no Actions PR approvals      | Actions enabled                                    |
| Outside-contributor fork PR approval                                  | Public + Actions enabled                           |
| Immutable releases; `pypi`/`release` envs restricted to `v*`          | Public + release or env                            |
| Private vulnerability reporting; `Protect default branch` ruleset     | Public                                             |

- **Immutable releases & env policies**: upload assets before publishing and rerun baseline after a repo's first release. Environment `PUT` preserves reviewers/`prevent_self_review`/`wait_timer`; extra deploy policies appear in `drift` with `DELETE` paths for approval.
- **Ruleset overwrite semantics**: `Protect default branch` blocks deletion/force-pushes without requiring PRs or signatures; `--apply` overwrites an existing owned ruleset of that name via `PUT` (resetting manual edits) and aborts with IDs if duplicates exist.

## Gotchas

- **Free-plan & secret-scanning limits**: private/internal secret scanning needs Secret Protection/GHAS; private rulesets (403 on Free) and public-only vulnerability reporting are noted, not forced. Paid secret-scanning subfeatures stay `disabled` silently.
- **Organization rulesets**: `rules/branches/<branch>` merges org and repo rules; mutate only the repo's owned ruleset.
- **Owner-level `SECURITY.md`**: public `<owner>/.github` (`gh api repos/<owner>/.github/contents/SECURITY.md`) covers public repos unless repo-specific scope needs a root `SECURITY.md` ([SECURITY.md template](../../../templates/SECURITY.md)).
- **Personal repos & orgs**: user repos reject collaborator downgrade to `pull` (422; remove inactive collaborators instead). Harden orgs once (2FA, SHA pins, GitHub-recommended security) with temporary `dot login github --grant admin:org`, then `dot login github`.

## Documentation

- [Rulesets API](https://docs.github.com/en/rest/repos/rules) · [Dependabot API](https://docs.github.com/en/rest/repos/repos#enable-dependabot-security-updates) · [Vulnerability reporting API](https://docs.github.com/en/rest/repos/repos#enable-private-vulnerability-reporting-for-a-repository)
- [Actions permissions](https://docs.github.com/en/rest/actions/permissions) · [Immutable releases](https://docs.github.com/en/code-security/supply-chain-security/understanding-your-software-supply-chain/immutable-releases) · [Default health files](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)
