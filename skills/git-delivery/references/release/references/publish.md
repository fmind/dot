# Prepare and Publish a Release

Use the repository's release task when it owns versioning, tags, or publication. The manual sequence below is a fallback; inspect the release trigger before starting and choose one publication owner.

## Workflow

1. **Check the preconditions**:
   - `main` synced with `origin`; unrelated edits stay unstaged and out of the release commit (gate them per the dirty-tree rule).
   - Identify every required hosted CI workflow and matrix job. Publication must qualify the final release commit, including any version and changelog edits; a green earlier commit, local gate, or CD job does not cover it.
   - The proposed tag is absent locally and remotely; stop if either copy exists and never move a published tag.
   - Identify whether publication is triggered by a tag, a branch push, or workflow dispatch. Follow that contract; a workflow-owned release skips the manual `gh release create` step.
1. **Compute the next version**: from the commit types since the last tag, `feat` → minor, `fix` and others → patch, `!` or `BREAKING CHANGE` → major:

   ```bash
   git-cliff --bumped-version
   ```

1. **Bump non-VCS-versioned manifests**: Python `version` in `pyproject.toml` (unless `hatch-vcs` or similar); inspect OpenTofu projects for explicit version constants; VCS-versioned projects need no separate manifest bump.
1. **Generate the changelog for that version**:

   ```bash
   git-cliff --bump -o CHANGELOG.md
   ```

1. **Gate the prepared candidate**: run the full gate (`mise run all`) after all version and changelog edits. When the tree carries unrelated changes, apply the [dirty-tree rule](../../../../mise/SKILL.md#gotchas). Include any resulting task-owned formatting fixes in the release commit.

1. **Commit the release**: the `chore(release)` subject is excluded from the changelog by design:

   ```bash
   git add CHANGELOG.md   # plus the manifest bumped above, if any
   git commit -m "chore(release): vX.Y.Z"
   ```

1. **Tag and push the exact release commit atomically**:

   ```bash
   tag=vX.Y.Z
   release_sha=$(git rev-parse HEAD)
   git tag -a "$tag" -m "$tag" "$release_sha"
   git push --atomic origin main "refs/tags/$tag"
   ```

1. **Require final-commit CI**: for a CLI-owned release, wait until every required workflow and matrix job at `release_sha` is present, completed, and successful. An empty list or pending run is incomplete proof; inspect jobs through [verification](verify.md), then publish. A workflow-owned release must enforce its own CI dependency for the final tagged commit; follow that contract without creating a competing release.

   ```bash
   gh run list --commit "$release_sha" --limit 100 --json workflowName,headSha,status,conclusion,url
   ```

1. **Publish through the selected owner**: for a workflow-owned release, wait for that workflow and follow [verification](verify.md). Only for a CLI-owned release, create a draft with the latest changelog section as notes, written to a temporary file to stay shell-agnostic:

   ```bash
   release_tmp=$(mktemp -d)
   git-cliff --latest --strip all > "$release_tmp/release-notes.md"
   gh release create "$tag" --verify-tag --draft --title "$tag" --notes-file "$release_tmp/release-notes.md"
   ```

   Upload the reviewed asset inventory, if any, while the release is still a draft; inspect `gh release view "$tag" --json assets` and download the draft assets to compare their names and checksums against the reviewed local inventory before publishing. Skip the upload for a release without assets. Release attestations are checked after publication through [verification](verify.md). Always prepare assets before publication: an earlier release's `isImmutable` does not prove the policy for a new release, and immutable releases cannot accept later asset changes.

   ```bash
   gh release upload "$tag" <asset>...
   gh release edit "$tag" --draft=false
   ```

1. **Verify and report**: use [verification](verify.md), then remove only the temporary notes directory created above after preserving any needed failure evidence.
