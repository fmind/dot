# Official gh Skills

Upstream `cli/cli` publishes agent skills under `skills/`, including `gh` (GitHub CLI invocation patterns, same name as this connector) and `gh-skill`. Preview a pinned candidate and compare it with [the connector](../SKILL.md); never install the upstream `gh` beside it, and install other skills only through the shared [vendor-skill policy](../../agent-project/references/vendor-skills.md#name-collisions). An unpinned `gh skill install` resolves the latest release, or the default branch, at install time.

Every `gh skill` subcommand is in preview and subject to change without notice; check `gh skill <command> --help` before relying on a flag.

```bash
gh skill search github --owner cli --json repo,skillName,description
gh skill preview cli/cli <name>@<commit>
gh skill install cli/cli <name> --pin <commit>   # only on the policy's pinned path
```
