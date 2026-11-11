---
name: trivy
description: "Scan dependencies, IaC, images, and licenses; generate SBOMs."
---

# Trivy

Scan non-`uv` dependencies, IaC, images, licenses, and SBOMs with committed `trivy.yaml` (`exit-code: 1` required to block; omit `secret` from `scan.scanners` so [betterleaks](../betterleaks.md) stays sole secret scanner; pure-Python repos without containers or IaC rely on `uv audit` + [jactionlint](../../../github-actions/references/jactionlint.md)). Check active scanners, severities, exclusions, and `ignore-unfixed` before claiming coverage (`uv.lock` and `aube-lock.yaml` carry no license metadata, so `license` evaluates container/OS and installed package metadata).

## Commands

```bash
trivy --config trivy.yaml fs .                                    # repository: deps, IaC, licenses
trivy --config trivy.yaml config .                                # IaC only: Dockerfile, Terraform, Kubernetes, GitHub Actions
trivy --config trivy.yaml image --skip-dirs '' --input tmp/image.tar             # local image tarball, before any push (check:image)
trivy --config trivy.yaml image --skip-dirs '' <registry>/<slug>@<digest>        # pushed image, by immutable digest
trivy --config trivy.yaml image --skip-dirs '' --format cyclonedx -o sbom.json <registry>/<slug>@<digest>
trivy --config trivy.yaml fs --tf-vars terraform.example.tfvars . # OpenTofu modules need variables to evaluate
```

## Mise Task

Wire `check:scan` into `check:network` (or `check`) per [mise](../../../mise/SKILL.md) and [task conventions](../../../mise/references/task-conventions.md#conventions), alongside `check:vuln` (`uv audit` for `uv.lock` semantics); use [unfixed-report.md](references/unfixed-report.md) for scheduled informational visibility:

```toml
[tasks."check:scan"]
description = "Scan dependencies, IaC, and licenses (Trivy)"
run = "trivy --config trivy.yaml fs ."
```

## Triage

1. **Ignore IDs, never severities**: document accepted risks in `.trivyignore` (with `#` reason) or path/expiry/license rules in `.trivyignore.yaml` (`--ignorefile`; [filtering](https://trivy.dev/docs/latest/configuration/filtering/)).
1. **Route secrets to [betterleaks](../betterleaks.md)** for verification and authorized rotation.

## Gotchas

- **Pass `--config trivy.yaml` explicitly**: `--config` > `TRIVY_CONFIG` > `./trivy.yaml`, so bare `trivy fs .` uses the shell's global `TRIVY_CONFIG`; scan untrusted repos from outside with independent `--config`/`--ignorefile`.
- **Disable telemetry in `trivy.yaml`**: set `scan.disable-telemetry: true` and `scan.skip-version-check: true` (`--debug` verifies).
- **Pass `--skip-dirs ''` on images** so repo `**/.venv` exclusions do not hide `/app/.venv` packages, and scan immutable `@<digest>` refs rather than mutable tags.
- **Keep license gates honest**: resolve Debian/package license hits against project distribution policy instead of blanket ignores.
- **Map `aube-lock.yaml`**: Trivy reads `uv.lock` natively but needs `pnpm:aube-lock\.yaml` in `scan.file-patterns`.
- **Air-gapped runs**: pre-cache DBs/checks and pass `--skip-db-update`, `--skip-java-db-update`, `--skip-check-update`, and `--offline-scan` ([air-gap docs](https://trivy.dev/docs/latest/advanced/air-gap/)), reporting DB age and gaps.

## Documentation

- [Trivy](https://trivy.dev) · [releases](https://github.com/aquasecurity/trivy/releases) · [changelog](https://github.com/aquasecurity/trivy/blob/main/CHANGELOG.md)
- Companion skills: [code-review](../code-review/GUIDE.md), [containerize](../../../docker/references/containerize/GUIDE.md), [github-actions](../../../github-actions/references/ci-cd/GUIDE.md).
