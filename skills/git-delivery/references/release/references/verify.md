# Verify a Published Release

Read-only post-publication audit (never edits releases, moves tags, or re-uploads assets).

1. **Pin expected identity** from the approved candidate (not current `main`):

   ```bash
   repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
   tag=vX.Y.Z
   release_sha=$(git rev-parse HEAD)
   ```

1. **Check the peeled remote tag** (`refs/tags/$tag^{}` must match `release_sha`; the unpeeled line is the tag object):

   ```bash
   git ls-remote --exit-code --tags origin "refs/tags/$tag" "refs/tags/$tag^{}"
   ```

1. **Inspect release metadata** (`targetCommitish` may say `main` and never substitutes for the peeled tag check):

   ```bash
   gh release view "$tag" -R "$repo" --json tagName,name,isDraft,isPrerelease,isImmutable,publishedAt,targetCommitish,assets,url
   ```

1. **Confirm exact-commit workflows** all completed green on `release_sha`:

   ```bash
   gh run list -R "$repo" --commit "$release_sha" --limit 100 --json workflowName,attempt,headSha,status,conclusion,event,url
   ```

1. **Verify assets and attestations** per [verify-assets](verify-assets.md).
1. **Smoke-test the shipped artifact** and its reported version ([containerize](../../../../docker/references/containerize/GUIDE.md) for `@sha256:` OCI, Cosign, and SBOM checks).
1. **Report receipt**: highest proven rung on the [proof ladder](../../../../full-review/SKILL.md#proof-ladder), `release_sha`, tag object + peeled SHA, workflow URLs, release URL/state, asset/checksum/attestation results, and verified artifact version.
