# Prepare and Publish a Release

## Workflow

1. **Check the preconditions**:
   - Clean working tree on `main`, synced with `origin`.
   - The proposed tag is absent locally and remotely; stop if either copy exists and never move a published tag.
   - A repository workflow that owns release creation runs from the pushed tag; verify its result instead of publishing a second release from the CLI.
1. **Gate**: Run the full gate (`mise run all`); if the tree carries unrelated changes and the gate write-formats, run it in an isolated working-tree copy containing the candidate edits or fall back to `mise run check` and `mise run test` (see [mise](../mise/SKILL.md)).
1. **Compute the next version** from the commit types since the last tag: `feat` → minor, `fix` and others → patch, `!` or `BREAKING CHANGE` → major:

   ```bash
   git-cliff --bumped-version
   ```

1. **Bump manifests** that are not VCS-versioned: Python `version` in `pyproject.toml` (unless `hatch-vcs` or similar); inspect OpenTofu projects for explicit version constants; VCS-versioned projects need no separate manifest bump.
1. **Generate the changelog** for that version:

   ```bash
   git-cliff --bump -o CHANGELOG.md
   ```

1. **Commit the release**; the `chore(release)` subject is excluded from the changelog by design:

   ```bash
   git add CHANGELOG.md   # plus the manifest bumped above, if any
   git commit -m "chore(release): vX.Y.Z"
   ```

1. **Tag and push the exact release commit** atomically:

   ```bash
   tag=vX.Y.Z
   release_sha=$(git rev-parse HEAD)
   git tag -a "$tag" -m "$tag" "$release_sha"
   git push --atomic origin main "refs/tags/$tag"
   ```

1. **Publish** with the latest changelog section as notes, written to a temporary file to stay shell-agnostic:

   ```bash
   release_tmp=$(mktemp -d)
   git-cliff --latest --strip all > "$release_tmp/release-notes.md"
   gh release create "$tag" --verify-tag --title "$tag" --notes-file "$release_tmp/release-notes.md"
   ```

1. **Report** the release URL and the resolved version, then run the verification below.
