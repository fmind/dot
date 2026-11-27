# Python PyPI & OCI Container CD

Reference for [cd.yml](../templates/cd.yml) and [image-platforms.py](../templates/image-platforms.py), triggered by `v*` tags after `validate` passes `mise run all`.

## Setup

- **Copy CD assets**: copy [cd.yml](../templates/cd.yml) to `.github/workflows/cd.yml` and stdlib-only [image-platforms.py](../templates/image-platforms.py) to `.github/scripts/image-platforms.py`.
- **Gate deploy targets**: set repository variables `ENABLE_DEPLOY_PYPI` and/or `ENABLE_DEPLOY_CONTAINER` to `true` only after `validate` passes `mise run all` (which must build `dist/*.whl` and `dist/*.tar.gz`).
- **PyPI Trusted Publisher**: create the `pypi` environment and register the Trusted Publisher matching owner, repo, workflow filename (`cd.yml`), and `pypi` environment verbatim.
- **Container prerequisites**: include Sigstore disclosure ([cosign](../../../../containers/references/docker/references/cosign.md)), [containerize](../../../../containers/references/containerize/GUIDE.md) `Dockerfile`, `trivy.yaml`, and pinned `trivy` + `cosign` in `mise.toml`.

## PyPI Pipeline

- **Separate build, attest, and publish**: build `dist/` without OIDC, verify tag == `v$(uv version --short)` and `python-package.sha256`, attest provenance in an isolated job (`actions/attest` after verifying hashes and file count), and grant `id-token: write` solely to `pypa/gh-action-pypi-publish`.
- **Preserve PEP 740 attestations**: `pypa/gh-action-pypi-publish` signs PEP 740 `publish/v1`; never pre-create `*.publish.attestation` or split uploads.
- **Multi-platform releases**: call `ci.yml` via `workflow_call` from `cd.yml` when wheels require multiple runners.

## OCI Container Pipeline

- **Verify candidate images before promotion**: push `:candidate-<sha>`, resolve `PLATFORMS` digests via `python3 -I .github/scripts/image-platforms.py`, run the [cosign release sequence](../../../../containers/references/docker/references/cosign.md#release-sequence) per child (signing the index once; Trivy defaults to AMD64), then promote via [Buildx imagetools](https://docs.docker.com/reference/cli/docker/buildx/imagetools/create/).
- **Lowercase only the GHCR repo path**: cosign OIDC certificates preserve workflow filename casing.
- **Disable CI caches on deploy**: pass `cache: false` to `jdx/mise-action` (or `setup-mise`) and `cache-binary: false` on Buildx in release/deploy jobs to prevent cache poisoning.
