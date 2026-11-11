# Official gh Skills

Upstream `cli/cli` ships `skills/` entries including `gh` (never install beside [this connector](../SKILL.md)) and `gh-skill`. Preview pinned commits and follow the [vendor-skill policy](../../agent-project/references/vendor-skills.md#name-collisions) (unpinned installs track latest release/default branch; `gh skill` subcommands are preview — check `--help`):

```bash
gh skill search gh --owner cli --json repo,skillName,description
gh skill preview cli/cli <name>@<commit>
gh skill install cli/cli <name> --pin <commit>   # only on the policy's pinned path
```
