---
name: cloud-run
description: Deploy a uv-managed Python container to Cloud Run with Artifact Registry, keyless CI, Secret Manager, and dedicated identities. Use to ship a Python service to GCP.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/cloud-run
  created: "2026-08-07"
  updated: "2026-09-06"
---

# Cloud Run Deployment

Deploy a Python service to Cloud Run through an immutable image digest, private invocation, keyless CI, and a dedicated runtime identity. [containerize](../containerize/SKILL.md) owns the image; [gcloud](../gcloud/SKILL.md) owns account, project, and region context.

## Workflow

1. **Resolve target and authority**: verify the gcloud account, project, region, service, Artifact Registry image repository, runtime permissions, and approved mutation scope.
1. **Configure identities once**: read [bootstrap.md](references/bootstrap.md) for APIs, registry, runtime service account, deployer service account, and Workload Identity Federation. Keep deployer and runtime identities distinct.
1. **Install the deployment toolchain**: pin Trivy and Cosign to exact stable versions in the Python project's mise configuration, lock them, and install them before any image scan or registry push; use [deployment.md](references/deployment.md).
1. **Validate locally**: build the pinned non-root Python image and run its tests and `check:image` scan per [containerize](../containerize/SKILL.md).
1. **Publish and prove provenance**: after push authority is explicit, follow [deployment.md](references/deployment.md). Extract one digest from BuildKit metadata, scan it, generate an SBOM, sign it, verify the expected identity and issuer, and attest the SBOM before deployment.
1. **Deploy privately**: pass the digest reference and dedicated `--service-account`; keep `--no-allow-unauthenticated`. Use [service.yaml](references/service.yaml) when settings warrant a declarative service specification.
1. **Use infrastructure as code when needed**: manage repeatable services, IAM, registries, and fleet-level infrastructure per [terraform](../terraform/SKILL.md); review the plan before apply.
1. **Wire CD when requested**: adapt [deploy.yml](references/deploy.yml), set its `GCP_*` variables and full `GCP_ARTIFACT_IMAGE`, then opt in with `ENABLE_DEPLOY_CLOUDRUN=true`.
1. **Verify the live result**: record the ready revision, deployed digest, runtime account, IAM policy, health result, and traffic split. Keep a known-good revision for rollback.

## Gotchas

- **One digest**: build, scan, signature, attestation, deployment, verification, and rollback must refer to the same `@sha256:` image.
- **Private by default**: grant `roles/run.invoker` only to intended callers or use an authenticating load balancer.
- **Listen on `$PORT`**: Cloud Run injects the port, normally 8080; a hardcoded listener fails revision health checks.
- **Request-scoped CPU**: background work can pause between requests. Use explicit always-on CPU only when its cost is justified, or use a Cloud Run job for batch work.
- **Scale deliberately**: keep minimum instances at zero unless measured first-request latency justifies idle cost.
- **Regional alignment**: keep the service and Artifact Registry repository in one region and project. Workload Identity Federation pools remain global.
- **External mutations**: registry pushes, signing, IAM changes, infrastructure apply, deployment, and traffic changes require authority for the named target.

## Official Skills

Upstream: `google/skills` (`skills/cloud`), listed and installed through [google-cloud](../google-cloud/SKILL.md); select the Cloud Run and CLI guardrail skills needed for the task.

## Documentation

- [Cloud Run](https://cloud.google.com/run/docs) · [Artifact Registry](https://cloud.google.com/artifact-registry/docs) · [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- Companion skills: [containerize](../containerize/SKILL.md), [github-actions](../github-actions/SKILL.md), [sops-secrets](../sops-secrets/SKILL.md), [gcloud](../gcloud/SKILL.md), [terraform](../terraform/SKILL.md), and [secure](../secure/SKILL.md).
