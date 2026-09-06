---
name: cloud-run
description: Deploy container images to Google Cloud Run with Artifact Registry, keyless CI identity, Secret Manager, ko, or Dockerfiles. Use to ship a service or agent to GCP.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/cloud-run
  created: "2026-08-07"
  updated: "2026-09-05"
---

# Cloud Run Deployment

Deploy services and agents to Cloud Run with private invocation, keyless CI, and a dedicated runtime identity. [containerize](../containerize/SKILL.md) owns images; [gcloud](../gcloud/SKILL.md) owns account/project context.

## Workflow

1. **Resolve target and authority**: project, region, service, expected image, runtime permissions, and the approved deployment scope; use gcloud to verify context.
1. **Configure identities**: read [bootstrap.md](references/bootstrap.md) for one-time APIs, registry, and WIF setup. Keep deployer and runtime service accounts distinct.
1. **Build and validate**: local packaging is the default. An authorized deployment explicitly passes `--push=true`, then requires ko's image-reference file to contain one digest; use [deployment.md](references/deployment.md).
1. **Deploy**: use the dedicated `--service-account` and private access default. Read [service.yaml](references/service.yaml) when settings need a service specification, or [terraform-stack](../terraform-stack/SKILL.md) for IaC.
1. **Wire CI when requested**: adapt [deploy.yml](references/deploy.yml), including `GCP_DEPLOY_SA`, `GCP_RUNTIME_SA`, and the opt-in variable. A failed build must emit no deployment output.
1. **Verify**: inspect the resulting revision, image digest, runtime account, access policy, health, and traffic; record a known revision for rollback.

## Gotchas

- **Digest, not tag**: deploy the `@sha256:` reference; `gcloud run services update-traffic` then rolls back to an exact revision.
- **Private by default**: keep `--no-allow-unauthenticated`; grant `roles/run.invoker` to callers or front the service with an authenticating load balancer.
- **Listen on `$PORT`**: Cloud Run injects `PORT` (default 8080); a hardcoded port fails the revision health check.
- **CPU is request-scoped**: background goroutines stall between requests; use `--no-cpu-throttling` for always-on work or a Cloud Run job for batch.
- **Cold starts**: set `--min-instances=1` only when first-hit latency matters more than the idle cost.
- **One region**: the Artifact Registry repository and the service share one region and project (cross-region pulls add latency and egress); WIF pools are global (`--location=global`).

## Official Skills

Upstream: `google/skills` (`skills/cloud`), listed and installed through [google-cloud](../google-cloud/SKILL.md); pick the Cloud Run and CLI guardrail skills.

## Documentation

- [Cloud Run](https://cloud.google.com/run/docs) · [ko](https://ko.build) · [google-github-actions/auth](https://github.com/google-github-actions/auth) · [deploy-cloudrun](https://github.com/google-github-actions/deploy-cloudrun)
- Companion skills: [containerize](../containerize/SKILL.md) (image), [github-actions](../github-actions/SKILL.md) (CD), [sops-secrets](../sops-secrets/SKILL.md) (secrets), [gcloud](../gcloud/SKILL.md) (context), [terraform-stack](../terraform-stack/SKILL.md) (IaC).
