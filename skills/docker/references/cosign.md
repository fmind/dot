---
name: cosign
description: "Sign, verify, and attest image digests with keyless Sigstore."
---

# Cosign

Sign and verify OCI `@sha256:` digests keylessly via Sigstore OIDC ([containerize](containerize/GUIDE.md) builds images; [ci-cd](../../github-actions/references/ci-cd/GUIDE.md) wires CD).

## Release sequence

Run in order on one immutable `@sha256:` digest, stopping on any failure:

1. **Scan and emit CycloneDX SBOM** via [trivy](../../code-security/references/trivy/GUIDE.md) (per platform child on multi-arch indexes).
1. **Sign the digest**, then verify against expected certificate identity and OIDC issuer.
1. **Attest the SBOM** to the digest it describes, then verify the attestation.
1. **Promote or deploy** only that verified `@sha256:` digest.

## Commands

Public Sigstore logs signing identity, certificate, signature, and digest permanently in public transparency logs — even for private registries. Confirm that disclosure is covered by publication authority (or configure private signing first); `--yes` skips interactive prompts without granting authority:

```bash
cosign sign --yes <registry>/<slug>@<digest>
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

Pin Cosign per project (`mise use --pin cosign` + `mise lock`, upgraded via [upgrade-tools](../../upgrade-tools/SKILL.md); workstation global `cosign` is for ad-hoc verification and never replaces project pins). Grant the signing job `id-token: write` and `packages: write` (or registry equivalent), set `cache: false` on `jdx/mise-action`, and sign the build output's `@sha256:` digest as in `cd.yml` ([ci-cd](../../github-actions/references/ci-cd/GUIDE.md)).

## Gotchas

- **Never sign mutable tags**: always sign `@sha256:` digests.
- **Pin `--certificate-identity` and `--certificate-oidc-issuer`** on every verification.
- **Signing mutates the registry**: `sign` and `attest` push artifacts, requiring registry-write authority.
- **Scan and attest every platform child** before promoting a multi-arch index (an index signature covers child descriptors, while Trivy scans/SBOMs target single platforms).

## Documentation

- [Cosign](https://docs.sigstore.dev/cosign/) · [Keyless overview](https://docs.sigstore.dev/cosign/signing/overview/) · [releases](https://github.com/sigstore/cosign/releases) · [changelog](https://github.com/sigstore/cosign/blob/main/CHANGELOG.md)
- Companions: [containerize](containerize/GUIDE.md), [ci-cd](../../github-actions/references/ci-cd/GUIDE.md), [code-security](../../code-security/references/code-review/GUIDE.md).
