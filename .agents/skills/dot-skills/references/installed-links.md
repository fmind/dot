# Recover Installed Skill Links

Use this guide when installed links need attention. Normal catalog edits follow [dot-skills](../SKILL.md); chezmoi owns creation of current links in the shared `~/.agents/skills/` directory.

## Retired links

After removing or renaming a declaration, chezmoi leaves its previously installed link in place. Inspect the exact link with `readlink` and compare its literal target with the retired checkout path. Within explicit cleanup authority, move only that confirmed link to a fresh backup path outside the shared catalog; refuse to replace an existing backup. Re-run apply to create any new declaration. Preserve replacement packages, links owned elsewhere, and the shared directory. `dot` no longer discovers or deletes former chezmoi targets automatically.

## Catalog consolidation migration

The frozen migration inventory covers the 58 names retired since v6.1.0. From the updated source checkout, preview it, then apply it when cleanup is authorized:

```bash
mise run migrate:skills
mise run migrate:skills -- --apply
mise run apply
uv run --frozen dot agent context --project . --check
```

The migration moves only symlinks whose literal target is this checkout's retired `skills/<name>` path, and skips any name declared active again. Directories, ordinary files, and links owned elsewhere are preserved and reported. Each apply creates a fresh backup under `~/.agents/retired-skill-links/`, outside the shared discovery directory. Re-running after success is a no-op. If interrupted, completed moves remain in the reported backup and a retry handles remaining links. To undo a move, inspect its saved target and move it back only if the original catalog name is still absent; never overwrite a replacement package. Restart agent sessions after successful verification.

## Name collisions

Apply rejects an active name owned elsewhere, including dangling links, even with `--force`. Inspect the existing owner, then choose a unique name or explicitly relocate the conflicting package before applying. Never overwrite another package to make validation pass.

## Source relocation

Moving this checkout leaves installed links pointing at the old location. Inspect affected links with `readlink`, then `unlink` only confirmed links to the old checkout; apply from the new source recreates them. Another checkout's links are never adopted automatically.

## Catalog ownership

The shared catalog must be a real directory. Apply rejects a whole-catalog symlink, including one pointing at this checkout, before changing its target. Per-name collision protection remains necessary for independently installed packages.

## Verification

Run `mise run check:skills` to check both catalogs and their local links, and inspect `~/.agents/skills` for the expected repository links. A healthy filesystem does not prove host selection; exercise the skill in the affected host separately.
