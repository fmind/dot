# Cloud Run Project and Identity Setup

1. **Pick the tier**: `gcloud run deploy` for one service; [service.yaml](service.yaml) via `gcloud run services replace` once settings accumulate; [terraform](../../terraform/SKILL.md) for a fleet.
1. **Set up the project once**: enable the APIs, create the Artifact Registry repository, and create a dedicated runtime service account (never the default compute SA; grant it only what the app reads).

   ```bash
   gcloud services enable run.googleapis.com artifactregistry.googleapis.com iamcredentials.googleapis.com
   gcloud artifacts repositories create <slug> --repository-format=docker --location=<region>
   gcloud iam service-accounts create <slug>-runtime   # runtime identity, least privilege
   ```

1. **Create the keyless CI identity**: one Workload Identity Federation pool and provider per project, plus a deployer service account that GitHub Actions impersonates over OIDC, so no key is ever exported.

   ```bash
   gcloud iam workload-identity-pools create github --location=global
   gcloud iam workload-identity-pools providers create-oidc github-actions \
     --location=global --workload-identity-pool=github \
     --issuer-uri="https://token.actions.githubusercontent.com" \
     --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
     --attribute-condition="assertion.repository_owner=='<owner>'"
   gcloud iam service-accounts create <slug>-deployer
   gcloud iam service-accounts add-iam-policy-binding "<slug>-deployer@<project>.iam.gserviceaccount.com" \
     --role=roles/iam.workloadIdentityUser \
     --member="principalSet://iam.googleapis.com/projects/<project_number>/locations/global/workloadIdentityPools/github/attribute.repository/<owner>/<repo>"
   ```

   The deployer needs `roles/run.admin` and `roles/artifactregistry.writer` on the project plus `roles/iam.serviceAccountUser` on the runtime SA (that grant authorizes deploying as it).
