# Verify a Published Release

Use after publication, including when a workflow or another person created the release. Verification only reads and downloads public assets into a disposable directory; it never edits a release, moves a tag, or replaces an asset.

1. **Resolve the expected identity** from the approved candidate, not from the latest branch state:

   ```bash
   repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
   tag=vX.Y.Z
   release_sha=$(git rev-parse HEAD)   # from the approved candidate checkout
   ```

1. **Reconcile the remote tag**: an annotated tag lists its tag object and a peeled `^{}` line; compare the peeled commit to `release_sha`, the first line is not the release commit:

   ```bash
   git ls-remote --exit-code --tags origin "refs/tags/$tag" "refs/tags/$tag^{}"
   ```

1. **Inspect the release state**: tag, draft and prerelease flags, publication time, assets, immutability, URL; `targetCommitish` may only name `main` and does not replace the peeled-tag check:

   ```bash
   gh release view "$tag" -R "$repo" --json tagName,name,isDraft,isPrerelease,isImmutable,publishedAt,targetCommitish,assets,url
   ```

1. **Prove exact-head automation**: every expected workflow at `release_sha` is present, completed, and successful; a green latest-branch run is not proof:

   ```bash
   gh run list -R "$repo" --commit "$release_sha" --limit 100 --json workflowName,attempt,headSha,status,conclusion,event,url
   ```

1. **Verify published assets** (checksums, release attestations, build provenance) per [verify-assets](references/verify-assets.md); anything missing is a failed proof, not permission to regenerate it.
1. **Verify the delivered boundary**: run the packaged binary or installation contract and confirm its version; [containerize](../containerize/SKILL.md) covers digest-bound OCI, Cosign, and SBOM checks.
1. **Report a release receipt** ending with the highest proven rung of the [proof ladder](../production-readiness/SKILL.md):
   - Expected commit, remote tag object and peeled commit, workflow names and URLs.
   - Release URL and state, expected versus downloaded assets, checksum and attestation results, packaged version.
