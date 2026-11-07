# Recover Installed Skill Links

Use this guide when installed links need attention. Normal catalog edits follow [dot-skills](../SKILL.md); chezmoi owns creation of current links in the shared `~/.agents/skills/` directory.

## Retired links

Removing or renaming a declaration leaves its installed link in place unless `.chezmoiremove` lists it, which is the default path ([dot-skills](../SKILL.md)). For a link it missed, inspect the exact link with `readlink` and compare its literal target with the retired checkout path. Within explicit cleanup authority, move only that confirmed link to a fresh backup path outside the shared catalog; refuse to replace an existing backup. Re-run apply to create any new declaration. Preserve replacement packages, links owned elsewhere, and the shared directory. `dot orphan` reports former chezmoi targets recorded in its persistent state, including retired links; it never deletes them. Use the [orphan guide](../../../../skills/dot-cli/references/orphans.md) to interpret the recorded status before deciding how to handle a link. A dangling retired link makes `dot agent context` fail closed until it is moved.

## Source relocation

Moving this checkout leaves installed links pointing at the old location. Inspect affected links with `readlink`, then `unlink` only confirmed links to the old checkout; apply from the new source recreates them. Another checkout's links are never adopted automatically.
