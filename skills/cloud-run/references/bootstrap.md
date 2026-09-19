# Cloud Run Project and Identity Setup

Use the approved account/configuration and pass `--project=<project>` on each command per [gcloud](../../gcloud/SKILL.md). Resolve numeric GitHub owner and repository IDs before configuring federation; names can be reclaimed after deletion.

1. **Pick the tier**: `gcloud run deploy` for one service; [service.yaml](../templates/service.yaml) via `gcloud run services replace` once settings accumulate; [infra-as-code](../../infra-as-code/SKILL.md) for a fleet.
1. **Set up the project once**: enable the APIs, create the Artifact Registry repository, and create a dedicated runtime service account (never the default compute SA; grant it only what the app reads).

   ```bash
   gcloud services enable run.googleapis.com artifactregistry.googleapis.com iamcredentials.googleapis.com
   gcloud artifacts repositories create <slug> --repository-format=docker --location=<region>
   gcloud iam service-accounts create <slug>-runtime   # runtime identity, least privilege
   ```

1. **Create the keyless CI identity**: reuse an approved Workload Identity Federation pool/provider, or create a dedicated pair, plus a deployer service account that GitHub Actions impersonates over OIDC, so no key is ever exported.

   ```bash
   gcloud iam workload-identity-pools create github --location=global
   gcloud iam workload-identity-pools providers create-oidc github-actions \
     --location=global --workload-identity-pool=github \
     --issuer-uri="https://token.actions.githubusercontent.com" \
     --attribute-mapping="google.subject=assertion.sub,attribute.repository_id=assertion.repository_id,attribute.repository_owner_id=assertion.repository_owner_id" \
     --attribute-condition="assertion.repository_owner_id=='<owner_id>' && assertion.repository_id=='<repository_id>'"
   gcloud iam service-accounts create <slug>-deployer
   gcloud iam service-accounts add-iam-policy-binding "<slug>-deployer@<project>.iam.gserviceaccount.com" \
     --role=roles/iam.workloadIdentityUser \
     --member="principalSet://iam.googleapis.com/projects/<project_number>/locations/global/workloadIdentityPools/github/attribute.repository_id/<repository_id>"
   ```

   Separate bootstrap permissions from routine deployment. Use `roles/run.developer` at the required service/project scope, `roles/artifactregistry.writer` on the image repository when CI pushes, and `roles/iam.serviceAccountUser` on the runtime SA. Changing invocation IAM requires additional permissions; do that through an authorized bootstrap step rather than giving every deployment project-wide administration. Grant the runtime identity Secret Manager access only to the secrets it reads.

## Documentation

- [Deployment permissions](https://docs.cloud.google.com/run/docs/deploying#required_roles) · [Federation mappings and conditions](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)
