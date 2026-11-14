---
name: cloud-run
description: "Deploy Python services to Cloud Run with Artifact Registry and keyless CD."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/cloud-run
  created: "2026-09-16"
  updated: "2026-11-14"
---

# Cloud Run Deployment

Deploy Python services to Cloud Run via immutable `@sha256:` digests, private IAM, keyless OIDC CD, and dedicated runtime service accounts. [containerize](../docker/references/containerize/GUIDE.md) owns images; [gcloud](../gcloud/SKILL.md) owns account, project, and region selection.

## Workflow

1. **Confirm target and bootstrap once**: verify gcloud account, project, region, service, and Artifact Registry repo; run [bootstrap.md](references/bootstrap.md) for APIs, registry, separate runtime/deployer SAs, and WIF (`[infra-as-code](../infra-as-code/SKILL.md)` owns multi-service fleets).
1. **Validate locally**: pin, lock, and install Trivy + Cosign, build a non-root `linux/amd64` image, and pass `mise run all` + `check:image` ([deployment.md](references/deployment.md), [containerize](../docker/references/containerize/GUIDE.md)).
1. **Publish, sign, and deploy privately**: once authorized, build/push one `@sha256:` digest, run [cosign release sequence](../docker/references/cosign.md#release-sequence), deploy with `--service-account` + `--invoker-iam-check --no-allow-unauthenticated` (or [service.yaml](templates/service.yaml)), and optionally wire [deploy.yml](templates/deploy.yml) + [verify-private.py](templates/verify-private.py).
1. **Verify and report**: confirm private-IAM postcondition and health/readiness, then report ready revision, `@sha256:` digest, pinned secret versions, runtime SA, traffic split, and rollback revision.

## Gotchas

- **Bind every step to one `@sha256:` digest**: build, scan, sign, attest, deploy, verify, and roll back the exact same digest.
- **Default to private access**: grant `roles/run.invoker` narrowly, front with an authenticating LB, or pass `gcloud run deploy --iap` for browser users via [IAP](https://docs.cloud.google.com/run/docs/securing/identity-aware-proxy-cloud-run).
- **Promote named revisions, never `LATEST`**: deploy `no_traffic` candidates, test the tag URL, then shift 100% traffic to the verified revision and drop the tag.
- **Cap DB pools against `max_connections`**: keep `max_instances × (pool_size + max_overflow)` (SQLAlchemy defaults: `5 + 10` per worker) under `max_connections` minus admin headroom; add a pooler before raising limits.
- **Keep `minScale: 0` unless cold starts justify idle spend**: for hard ceilings, propose a Cloud Billing [spend cap](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps) (requires billing authority, lags slightly, and halts Cloud Run when exceeded).
- **Co-locate service and Artifact Registry** in the same project and region; WIF pools stay `global`.

## Task guides

<!-- guides:start -->

- [bootstrap](references/bootstrap.md): Bootstrap Cloud Run project APIs, Artifact Registry, service accounts, and WIF.
- [deployment](references/deployment.md): Build, scan, sign, deploy private Cloud Run revisions, and verify IAM.

<!-- guides:end -->

## Official Skills

Upstream `google/skills` (`skills/cloud`) installs via [google-developer](../gcloud/references/google-developer.md); [gcloud](../gcloud/SKILL.md) covers CLI guardrails.

## Documentation

- [Cloud Run](https://docs.cloud.google.com/run/docs) · [Artifact Registry](https://docs.cloud.google.com/artifact-registry/docs) · [Workload Identity Federation](https://docs.cloud.google.com/iam/docs/workload-identity-federation) · [Cloud Run releases](https://docs.cloud.google.com/run/docs/release-notes) · [Artifact Registry releases](https://docs.cloud.google.com/artifact-registry/docs/release-notes)
- Companions: [containerize](../docker/references/containerize/GUIDE.md), [github-actions](../github-actions/references/ci-cd/GUIDE.md), [gcloud](../gcloud/SKILL.md), [infra-as-code](../infra-as-code/SKILL.md), [code-security](../code-security/references/code-review/GUIDE.md).
