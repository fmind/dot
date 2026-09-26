---
name: trivy
description: "Dependency, configuration, image, license, and SBOM scanning."
---

# Trivy

Scan dependencies, infrastructure as code, secrets, licenses, container images, and SBOMs according to the project's `trivy.yaml`. Inspect its enabled scanners, severity, exclusions, and `ignore-unfixed` setting before claiming coverage. Blocking policies need `exit-code: 1`; findings otherwise default to a successful exit.

## Commands

```bash
trivy --config trivy.yaml fs .                                    # repository: deps, IaC, secrets, licenses
trivy --config trivy.yaml config .                                # IaC only: Dockerfile, Terraform, Kubernetes, GitHub Actions
trivy --config trivy.yaml image --skip-dirs '' --input tmp/image.tar             # local image tarball, before any push (check:image)
trivy --config trivy.yaml image --skip-dirs '' <registry>/<slug>@<digest>        # pushed image, by immutable digest
trivy --config trivy.yaml image --skip-dirs '' --format cyclonedx -o sbom.json <registry>/<slug>@<digest>
trivy --config trivy.yaml fs --tf-vars terraform.example.tfvars . # OpenTofu modules need variables to evaluate
```

## Mise Task

Expose the repository scan as `check:scan` in `mise.toml` per [mise](../../../mise/SKILL.md); `mise run check` then runs it locally and in CI:

```toml
[tasks."check:scan"]
description = "Scan dependencies, IaC, licenses, and secrets (Trivy)"
run = "trivy --config trivy.yaml fs ."
```

Python's native dependency scanner stays separate as `check:vuln` (`uv audit`) because it understands `uv.lock` semantics; keep both tasks, while `trivy fs` adds the configured IaC, secret, and license scanners.

For scheduled visibility into advisories that the blocking policy intentionally excludes, use the separate [fixed and unfixed report](references/unfixed-report.md). It never replaces the blocking gate.

## Triage

1. Group findings by severity, then split fixable from `unfixed`.
1. Prefer the minimal upgrade of the affected dependency or base image; re-run the scan to prove the fix.
1. Record an accepted risk in `.trivyignore` (one finding ID per line, with a `#` reason) instead of lowering the global severity bar. Use `.trivyignore.yaml` with explicit `--ignorefile` for path-scoped findings, expiry, or license ignores; see [filtering](https://trivy.dev/docs/latest/configuration/filtering/).
1. Verify a secret finding's exposure, then coordinate authorized rotation and cleanup per [gitleaks](../gitleaks.md); history rewrites require explicit authority.

## Gotchas

- **Untrusted candidates**: a project-owned policy is not an independent audit policy. Run outside the candidate with reviewed configuration, `--ignorefile`, secret rules, and exclusions; inspect environment overrides too. Preserve the repository policy for its normal gate and distinguish those results from the independent scan.
- **Always pass `--config trivy.yaml`**: precedence is `--config` > `TRIVY_CONFIG` > `./trivy.yaml`, and the owner's shell exports a global `TRIVY_CONFIG`, so a bare `trivy fs .` silently uses the global policy.
- **Commit a project `trivy.yaml`**: copy the global one so CI, hooks, and agents share one policy.
- **Image coverage**: pass `--skip-dirs ''` for image scans to clear repository-only exclusions. The Python image stores its application in `/app/.venv`; inheriting `**/.venv` silently hides those packages. Confirm that the report includes the expected Python packages.
- **License findings remain findings**: the shared license policy can reject Debian base packages. Review the owning project's distribution requirements and explicit license policy before publication; do not disable the scanner or add blanket ignores to make an image pass.
- **Scan digests, not tags**: a tag can move after the scan; the digest is what ships.
- **Offline scans**: cache the required vulnerability database, Java database, and checks bundle first. `--skip-db-update` alone does not prevent other downloads; use the applicable `--skip-java-db-update`, `--skip-check-update`, and `--offline-scan` options per the [network guide](https://trivy.dev/docs/latest/advanced/air-gap/). Report missing data and database age instead of claiming a fresh or complete offline scan.

## Documentation

- [Trivy](https://trivy.dev)
- Releases: [Trivy](https://github.com/aquasecurity/trivy/releases) · [changelog](https://github.com/aquasecurity/trivy/blob/main/CHANGELOG.md)
- Companion skills: [code-review](../code-review/GUIDE.md) (the repository checklist), [containerize](../../../containerize/references/image-build/GUIDE.md) (image scans), [github-actions](../../../github-actions/references/ci-cd/GUIDE.md) (`security.yml` scheduled scan).
