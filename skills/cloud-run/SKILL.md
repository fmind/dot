---
name: cloud-run
description: "Deploy Python services to Cloud Run with Artifact Registry and keyless CD."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/cloud-run
  created: "2026-09-16"
  updated: "2026-11-07"
---

# Cloud Run Deployment

Deploy a Python service to Cloud Run through an immutable image digest, private invocation, keyless CI, and a dedicated runtime identity. [containerize](../docker/references/containerize/GUIDE.md) owns the image; [gcloud](../gcloud/SKILL.md) owns account, project, and region context.

## Workflow

1. **Resolve target and authority**: verify the gcloud account, project, region, service, and Artifact Registry image repository; registry pushes, signing, IAM changes, deployment, and traffic changes each need authority for the named target.
1. **Configure identities once**: read [bootstrap.md](references/bootstrap.md) for APIs, registry, runtime service account, deployer service account, and Workload Identity Federation. Keep deployer and runtime identities distinct.
1. **Validate locally**: pin, lock, and install Trivy and Cosign before any image scan or registry push, then build the pinned non-root Python image and run its tests and `check:image` scan; follow [deployment.md](references/deployment.md) steps 1-2 and [containerize](../docker/references/containerize/GUIDE.md).
1. **Publish and prove provenance**: after push authority is explicit, follow [deployment.md](references/deployment.md): take one digest (the build action's output in CI, BuildKit metadata locally) and run the [cosign release sequence](../docker/references/cosign.md#release-sequence) on it before deployment.
1. **Deploy privately**: pass the digest reference and dedicated `--service-account`; keep `--invoker-iam-check --no-allow-unauthenticated` and verify both access controls after deployment. Use [service.yaml](templates/service.yaml) when settings warrant a declarative service specification; a successful update does not prove private IAM.
1. **Use infrastructure as code when needed**: manage repeatable services, IAM, registries, and fleet-level infrastructure per [infra-as-code](../infra-as-code/SKILL.md); review the plan before apply.
1. **Wire CD when requested**: adopt [deploy.yml](templates/deploy.yml) and [verify-private.py](templates/verify-private.py) per the "Wire CD" and "Roll out through a candidate" steps of [deployment.md](references/deployment.md).
1. **Verify the live result**: record the ready revision, deployed digest, pinned secret versions, runtime account, IAM policy, health result, and traffic split. Keep a known-good revision for rollback.

## Gotchas

- **Use one digest throughout**: build, scan, signature, attestation, deployment, verification, and rollback must refer to the same `@sha256:` image.
- **Private by default**: grant `roles/run.invoker` only to intended callers or use an authenticating load balancer. For signed-in users without a load balancer, `gcloud run deploy --iap` enables [IAP on the service](https://docs.cloud.google.com/run/docs/securing/identity-aware-proxy-cloud-run).
- **Promote an exact revision, never LATEST**: CD deploys a no-traffic tagged candidate, verifies it on the tag URL, then routes 100% to that revision name and drops the tag, so a later revision never inherits traffic unverified.
- **Size connection pools against the database limit**: keep `max_instances × (pool_size + max_overflow)` below the database's `max_connections` minus admin headroom (SQLAlchemy defaults to 5 + 10 per process), and add a connection pooler instead of raising pool sizes when autoscaling exhausts it.
- **Scale deliberately**: keep minimum instances at zero unless measured first-request latency justifies idle cost. For a hard monthly cost ceiling, propose a Cloud Billing [spend cap](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps): once estimated costs exceed the budget, it pauses the project's Cloud Run usage, taking the service offline until the cap is lifted or the month ends; enforcement lags, and setting it needs billing authority.
- **Align service and registry regions**: keep the service and Artifact Registry repository in one region and project. Workload Identity Federation pools remain global.

## Official Skills

Upstream: `google/skills` (`skills/cloud`), listed and installed through [Google catalog](../google-developer/SKILL.md). Select the Cloud Run skills the task needs; [gcloud](../gcloud/SKILL.md) covers its CLI guardrail skill.

## Documentation

- [Cloud Run](https://docs.cloud.google.com/run/docs) · [Artifact Registry](https://docs.cloud.google.com/artifact-registry/docs) · [Workload Identity Federation](https://docs.cloud.google.com/iam/docs/workload-identity-federation)
- Releases: [Cloud Run](https://docs.cloud.google.com/run/docs/release-notes) · [Artifact Registry](https://docs.cloud.google.com/artifact-registry/docs/release-notes)
- Companion skills: [containerize](../docker/references/containerize/GUIDE.md), [github-actions](../github-actions/references/ci-cd/GUIDE.md), [gcloud](../gcloud/SKILL.md), [infra-as-code](../infra-as-code/SKILL.md), and [code-security](../code-security/references/code-review/GUIDE.md).
