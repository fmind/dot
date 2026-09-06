# Cloud Run Deployment Commands

1. **Build and deploy**: the `build:image` task from [containerize](../containerize/SKILL.md) defaults to local output; an authorized deployment explicitly pushes to `KO_DOCKER_REPO=<region>-docker.pkg.dev/<project>/<slug>` and reads ko's image-reference file.

   ```bash
   set -euo pipefail
   mise run build:image -- --push=true --image-refs tmp/refs.txt
   IMAGE=$(cat tmp/refs.txt)
   [[ "$IMAGE" =~ ^[^[:space:]@]+@sha256:[[:xdigit:]]{64}$ ]]
   gcloud run deploy <slug> --image="$IMAGE" --region=<region> \
     --service-account="<slug>-runtime@<project>.iam.gserviceaccount.com" \
     --no-allow-unauthenticated
   ```

1. **Configure the service**: plain config rides `--set-env-vars=LOG_LEVEL=info`; secrets ride `--set-secrets=API_KEY=api-key:latest`, so the value never enters the spec or the revision history.

   ```bash
   sops -d secrets.enc.yaml | yq -r .api_key | gcloud secrets versions add api-key --data-file=-   # seed from sops-secrets
   ```

1. **Expose a `deploy` task**: run it on demand only, never from a git hook, because a deploy spends money and mutates production (see [mise](../mise/SKILL.md)).

   ```toml
   [tasks.deploy]
   description = "Deploy an image to Cloud Run — pass the digest ref as the argument"
   # mise appends CLI args to the last command: `mise run deploy <image-ref>`.
   run = "gcloud run deploy <slug> --region=<region> --service-account=<slug>-runtime@<project>.iam.gserviceaccount.com --no-allow-unauthenticated --image"
   ```

1. **Wire CD**: copy [deploy.yml](references/deploy.yml) into the `cd.yml` from [github-actions](../github-actions/SKILL.md), set the `GCP_*` variables (including distinct `GCP_DEPLOY_SA` and `GCP_RUNTIME_SA`) and `CLOUDRUN_SERVICE`, and opt in with `ENABLE_DEPLOY_CLOUDRUN=true`.
