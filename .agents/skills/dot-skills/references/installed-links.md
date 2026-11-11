# Recover Installed Skill Links

Recover stale skill links in `~/.agents/skills/`; routine catalog edits follow [dot-skills](../SKILL.md).

## Retired links

`.chezmoiremove` normally deletes retired links ([dot-skills](../SKILL.md)). If one remains (a dangling link makes `dot agent context` fail closed), check `readlink` against the retired checkout path and inspect `dot orphan` ([orphan guide](../../../../skills/dot-cli/references/orphans.md); `dot orphan` never deletes). With cleanup authority, move only that confirmed link to a non-existent backup path outside `~/.agents/skills/`, preserving third-party packages and replacement links, then re-run apply.

## Source relocation

Moving this checkout leaves symlinks pointing at the old path. Confirm each target with `readlink`, `unlink` only links to the old checkout, and re-run apply from the new location (foreign checkouts are never adopted automatically).
