# Recover Installed Skill Links

Use this guide when installed links need attention. Normal catalog edits follow [dot-skills](../SKILL.md); chezmoi owns creation of current links in the shared `~/.agents/skills/` directory.

## Retired links

After removing or renaming a declaration, chezmoi leaves its previously installed link in place. Inspect the exact link with `readlink` and compare its literal target with the retired checkout path. Within explicit cleanup authority, move only that confirmed link to a fresh backup path outside the shared catalog; refuse to replace an existing backup. Re-run apply to create any new declaration. Preserve replacement packages, links owned elsewhere, and the shared directory. `dot` no longer discovers or deletes former chezmoi targets automatically.

## Name collisions

Apply rejects an active name owned elsewhere, including dangling links, even with `--force`. Inspect the existing owner, then choose a unique name or explicitly relocate the conflicting package before applying. Never overwrite another package to make validation pass.

## Source relocation

Moving this checkout leaves installed links pointing at the old location. Inspect affected links with `readlink`, then `unlink` only confirmed links to the old checkout; apply from the new source recreates them. Another checkout's links are never adopted automatically.

## Legacy migration

Apply converts a whole-catalog symlink to this checkout into a real directory. If the old source catalog contains independently installed links, record their targets and move those links outside this checkout first; after migration, reinstall them individually in `~/.agents/skills/`. A catalog linked elsewhere requires explicit migration before applying.

Retain this compatibility path until supported installations are confirmed migrated or support for the old layout is explicitly retired. Completion on one workstation alone is insufficient; collision protection remains necessary afterward.

## Verification

Run `dot agent doctor --agent codex --explain` to check bounded filesystem metadata and expected repository links when chezmoi is available. Package names appear only on request; instruction bodies are never read. A healthy filesystem does not prove host selection; exercise the skill in the affected host separately.
