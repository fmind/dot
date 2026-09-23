---
name: cosign
description: "Image signatures, identity verification, and attestations."
---

# Cosign

Keyless signing with Sigstore: an OIDC identity (a GitHub Actions workflow or a developer's browser login) signs the image digest and anyone verifies it without managing keys; [containerize](image-build/GUIDE.md) builds the image and [github-actions](../../github-actions/references/ci-cd/GUIDE.md) wires the CD job.

## Commands

Public Sigstore records signing identity, certificate, signature, and artifact digest in permanent public transparency logs, including when the registry is private. Include that disclosure in the authorized publication scope; reuse existing authority when it already covers it. Otherwise prepare an approved signing setup that keeps certificate and transparency records private before signing. `--yes` suppresses consent prompts; it does not grant publication authority.

```bash
cosign sign --yes <registry>/<slug>@<digest>              # --yes avoids consent prompts after the signing scope is authorized
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

Resolve the exact Cosign version from the workstation baseline, add it to the project toolchain, and lock it before publishing; [upgrade-tools](../../upgrade-tools/SKILL.md) owns later upgrades.

## Gotchas

- **Sign digests, never tags**: a tag can be repointed after signing.
- **Verification pins identity and issuer**: a valid signature from an unexpected workflow is not provenance; record the expected identity in the release documentation.
- **Signing writes to the registry**: `sign` and `attest` push signatures next to the image, so a local packaging request does not authorize them.
- **SBOM first, then attest**: generate the SBOM per [trivy](../../security-review/references/trivy/GUIDE.md) and attach it as an attestation so consumers verify inventory and signature together.
- **Multi-platform images**: an index signature covers its child descriptors, but a scan or SBOM usually covers one platform. Scan every published child, attach each SBOM to that child's digest, and verify all children before promoting the index.

## Documentation

- [cosign](https://docs.sigstore.dev/cosign/) · [transparency and identity](https://docs.sigstore.dev/cosign/signing/overview/)
- Releases: [cosign](https://github.com/sigstore/cosign/releases) · [changelog](https://github.com/sigstore/cosign/blob/main/CHANGELOG.md)
- Companion skills: [containerize](image-build/GUIDE.md) (builds the image), [github-actions](../../github-actions/references/ci-cd/GUIDE.md) (CD job), [security-review](../../security-review/references/code-review/GUIDE.md).
