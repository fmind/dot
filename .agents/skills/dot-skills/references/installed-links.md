# Recover Installed Skill Links

Use this guide when installed links need attention. Normal catalog edits follow [dot-skills](../SKILL.md); chezmoi owns creation of current links in the shared `~/.agents/skills/` directory.

## Retired links

After removing or renaming a tracked declaration, run `dot chezmoi clean` to preview former managed targets, then `dot chezmoi clean --interactive` to approve moving the reviewed set into recoverable backups. Cleanup selects only links whose literal target still equals this checkout's `skills/<name>`; replacement packages and the shared directory survive. If the declaration was never tracked, inspect the installed link with `readlink` and explicitly `unlink` only that confirmed retired link.

## Name collisions

Apply rejects an active name owned elsewhere, including dangling links, even with `--force`. Inspect the existing owner, then choose a unique name or explicitly relocate the conflicting package before applying. Never overwrite another package to make validation pass.

## Source relocation

Moving this checkout leaves installed links pointing at the old location. Inspect affected links with `readlink`, then `unlink` only confirmed links to the old checkout; apply from the new source recreates them. Another checkout's links are never adopted automatically.

## Legacy migration

Apply converts a whole-catalog symlink to this checkout into a real directory. If the old source catalog contains independently installed links, record their targets and move those links outside this checkout first; after migration, reinstall them individually in `~/.agents/skills/`. A catalog linked elsewhere requires explicit migration before applying.

Retain this compatibility path until supported installations are confirmed migrated or support for the old layout is explicitly retired. Completion on one workstation alone is insufficient; collision protection remains necessary afterward.

## Verification

Run `dot agent doctor --agent codex --explain` to check bounded filesystem metadata and expected repository links when chezmoi is available. Package names appear only on request; instruction bodies are never read. A healthy filesystem does not prove host selection; exercise the skill in the affected host separately.
