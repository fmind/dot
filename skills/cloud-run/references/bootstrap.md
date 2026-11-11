# Cloud Run Project and Identity Setup

Pass `--project=<project>` with the approved account per [gcloud](../../gcloud/SKILL.md). Pin numeric GitHub `repository_owner_id` and `repository_id` in federation conditions so renamed/reclaimed accounts cannot impersonate.

1. **Choose the management tier**: `gcloud run deploy` for single services, [service.yaml](../templates/service.yaml) (`gcloud run services replace`) once settings grow, or [infra-as-code](../../infra-as-code/SKILL.md) for fleets.
1. **Bootstrap APIs, registry, and runtime SA** (never use the default compute SA; grant Secret Manager access only to secrets the app reads):

   ```bash
   gcloud services enable --project=<project> run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com \
     iam.googleapis.com iamcredentials.googleapis.com cloudresourcemanager.googleapis.com sts.googleapis.com
   gcloud artifacts repositories create <slug> --project=<project> --repository-format=docker --location=<region>
   gcloud iam service-accounts create <slug>-runtime --project=<project>
   ```

1. **Configure keyless GitHub Actions WIF** (no exported service-account keys):

   ```bash
   gcloud iam workload-identity-pools create github --project=<project> --location=global
   gcloud iam workload-identity-pools providers create-oidc github-actions \
     --project=<project> --location=global --workload-identity-pool=github \
     --issuer-uri="https://token.actions.githubusercontent.com" \
     --attribute-mapping="google.subject=assertion.sub,attribute.repository_id=assertion.repository_id,attribute.repository_owner_id=assertion.repository_owner_id,attribute.workflow_ref=assertion.workflow_ref" \
     --attribute-condition="assertion.repository_owner_id=='<owner_id>' && assertion.repository_id=='<repository_id>' && assertion.ref.startsWith('refs/tags/v') && assertion.workflow_ref.startsWith('<owner>/<repo>/.github/workflows/cd.yml@')"
   gcloud iam service-accounts create <slug>-deployer --project=<project>
   gcloud iam service-accounts add-iam-policy-binding "<slug>-deployer@<project>.iam.gserviceaccount.com" \
     --project=<project> --role=roles/iam.workloadIdentityUser \
     --member="principalSet://iam.googleapis.com/projects/<project_number>/locations/global/workloadIdentityPools/github/attribute.repository_id/<repository_id>"
   ```

   Protect `refs/tags/v*` with a GitHub [tag ruleset](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets) restricting tag create/update/delete to release maintainers ([repository](../../gh/references/repository/GUIDE.md) protects only the default branch).

   Grant the deployer `roles/run.developer`, `roles/artifactregistry.writer` on the image repo, `roles/iam.serviceAccountUser` on `<slug>-runtime`, `run.routes.invoke` for candidate checks, and `run.services.getIamPolicy` + `resourcemanager.projects.getIamPolicy` so CD's private-IAM check can reject any `allUsers` or `allAuthenticatedUsers` binding (including conditional or custom-role bindings). Keep `run.services.setIamPolicy` and org/folder public-access cleanup in authorized bootstrap rather than routine CD; see [Cloud Run public-access controls](https://docs.cloud.google.com/run/docs/authenticating/public).

## Documentation

- [Deployment permissions](https://docs.cloud.google.com/run/docs/deploying#required_roles) · [Federation mappings and conditions](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)
