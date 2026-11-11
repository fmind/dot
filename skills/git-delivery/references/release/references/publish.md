# Prepare and Publish a Release

Prefer the repository's native release task when defined; use this fallback only after confirming a single publication owner (CLI vs CI workflow).

## Workflow

1. **Verify preconditions**:
   - `main` matches `origin/main`; keep unrelated edits unstaged and gate via the [dirty-tree rule](../../../../mise/SKILL.md#gotchas).
   - List required CI workflows and matrix jobs (the final release commit itself must pass hosted CI).
   - Confirm the target tag exists neither locally nor on `origin`.
   - Confirm whether tag push, branch push, or `workflow_dispatch` owns GitHub Release creation.
1. **Compute the next tag** (`feat` → minor, `fix`/others → patch, `!`/`BREAKING CHANGE` → major; stop if unchanged from latest tag):

   ```bash
   tag=$(git-cliff --config pyproject.toml --bumped-version)
   ```

1. **Bump static manifests**: run `uv version "${tag#v}" --no-sync` for static Python versions (`pyproject.toml` + `uv.lock`) and check OpenTofu version constants; skip for VCS-versioned (`hatch-vcs`) packages.
1. **Update `CHANGELOG.md`** (`--prepend` preserves prior edits; use `-o CHANGELOG.md` only to initialize a missing file):

   ```bash
   git-cliff --config pyproject.toml --unreleased --tag "$tag" --prepend CHANGELOG.md
   ```

1. **Gate the release tree**: run `mise run format` and `mise run all` ([dirty-tree rule](../../../../mise/SKILL.md#gotchas) if needed) and include formatter updates.
1. **Commit**:

   ```bash
   git add CHANGELOG.md   # plus bumped manifests (pyproject.toml, uv.lock), if any
   git commit -m "chore(release): $tag"
   ```

1. **Tag and push atomically**:

   ```bash
   release_sha=$(git rev-parse HEAD)
   git tag "$tag" -m "$tag" "$release_sha"   # -m without -a keeps tag.forceSignAnnotated signing
   git push --atomic origin main "refs/tags/$tag"
   ```

1. **Wait for exact-commit CI**: for CLI-owned releases, require every workflow/matrix job on `release_sha` to complete green before publishing ([verify.md](verify.md)):

   ```bash
   gh run list --commit "$release_sha" --limit 100 --json workflowName,headSha,status,conclusion,url
   ```

1. **Publish via the single owner**: if CI owns releases, wait for it and run [verify.md](verify.md). For CLI-owned releases, stage a draft first because immutable releases freeze tags and assets upon publication:

   ```bash
   release_tmp=$(mktemp -d)
   git-cliff --config pyproject.toml --latest --strip all > "$release_tmp/release-notes.md"
   gh release create "$tag" --verify-tag --draft --title "$tag" --notes-file "$release_tmp/release-notes.md"
   ```

   Upload any release assets to the draft, download and verify their names and SHA-256 checksums via `gh release view "$tag" --json assets`, then publish:

   ```bash
   gh release upload "$tag" <asset>...
   gh release edit "$tag" --draft=false
   ```

1. **Verify and clean up**: run [verify.md](verify.md) and remove `$release_tmp`.
