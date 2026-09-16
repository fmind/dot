---
name: cosign
description: "Image signatures, identity verification, and attestations."
---

# Cosign

Keyless signing with Sigstore: an OIDC identity (a GitHub Actions workflow or a developer's browser login) signs the image digest and anyone verifies it without managing keys; [containerize](image-build/GUIDE.md) builds the image and [github-actions](../../github-actions/references/ci-cd/GUIDE.md) wires the CD job.

## Commands

```bash
cosign sign --yes <registry>/<slug>@<digest>              # --yes is mandatory: cosign prompts otherwise and hangs agents and CI
cosign verify \
  --certificate-identity 'https://github.com/<owner>/<repo>/.github/workflows/cd.yml@refs/tags/<tag>' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
  <registry>/<slug>@<digest>
cosign attest --yes --type cyclonedx --predicate sbom.json <registry>/<slug>@<digest>
cosign verify-attestation --type cyclonedx \
  --certificate-identity 'https://github.com/<owner>/<repo>/.github/workflows/cd.yml@refs/tags/<tag>' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
  <registry>/<slug>@<digest>
```

## GitHub Actions

Pin `cosign` in `mise.toml` `[tools]` so `mise-action` installs it with the rest of the toolchain; the signing job needs `permissions: id-token: write` plus `packages: write` (or the registry's equivalent), `cache: false` on `mise-action`, and signs the digest the build step recorded (`containerimage.digest` from Buildx metadata or the build-push action's `digest` output). The [github-actions](../../github-actions/references/ci-cd/GUIDE.md) `cd.yml` template implements this wiring.

```toml
[tools]
cosign = "latest"
```

## Gotchas

- **Sign digests, never tags**: a tag can be repointed after signing.
- **Verification pins identity and issuer**: a valid signature from an unexpected workflow is not provenance; record the expected identity in the release documentation.
- **Signing writes to the registry**: `sign` and `attest` push signatures next to the image, so a local packaging request does not authorize them.
- **SBOM first, then attest**: generate the SBOM per [trivy](../../security-review/references/trivy/GUIDE.md) and attach it as an attestation so consumers verify inventory and signature together.

## Documentation

- [cosign](https://docs.sigstore.dev/cosign/)
- Releases: [cosign](https://github.com/sigstore/cosign/releases) · [changelog](https://github.com/sigstore/cosign/blob/main/CHANGELOG.md)
- Companion skills: [containerize](image-build/GUIDE.md) (builds the image), [github-actions](../../github-actions/references/ci-cd/GUIDE.md) (CD job), [security-review](../../security-review/references/code-review/GUIDE.md).
