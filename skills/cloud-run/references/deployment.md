# Cloud Run Deployment Commands

1. **Pin and install image tools**: pin exact stable versions in `mise.toml`, lock, and install before scanning or pushing ([upgrade-tools](../../upgrade-tools/SKILL.md) owns upgrades).

   ```bash
   mise use --pin cosign trivy
   mise lock
   mise install --locked cosign trivy
   cosign version
   trivy --version
   ```

1. **Validate locally**: set `build:image` to `--platform linux/amd64` (even on ARM hosts), then run the full gate and local archive scan:

   ```bash
   uv sync --locked
   mise run all
   mise run check:image
   ```

1. **Build and push after authorization**: pass tagless `IMAGE_REPOSITORY` and capture BuildKit's validated `@sha256:` digest:

   ```bash
   set -euo pipefail
   export IMAGE_REPOSITORY="<region>-docker.pkg.dev/<project>/<repository>/<slug>"
   export TAG="<tag>"
   [[ "$IMAGE_REPOSITORY" =~ ^[^[:space:]@]+$ ]]
   [[ "$TAG" =~ ^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$ ]]
   gcloud auth configure-docker "<region>-docker.pkg.dev" --quiet
   mkdir -p tmp
   docker buildx build --platform linux/amd64 --push --tag "$IMAGE_REPOSITORY:$TAG" --metadata-file tmp/image-metadata.json .
   DIGEST="$(jq -er '."containerimage.digest" | select(test("^sha256:[0-9a-f]{64}$"))' tmp/image-metadata.json)"
   IMAGE="$IMAGE_REPOSITORY@$DIGEST"
   printf '%s\n' "$IMAGE" >tmp/image-ref.txt
   ```

1. **Scan, sign, and attest `$IMAGE`**: run the [cosign release sequence](../../docker/references/cosign.md#release-sequence) (public transparency-log disclosure applies even to private registries):

   ```bash
   trivy --config trivy.yaml image --skip-dirs '' --platform linux/amd64 "$IMAGE"
   trivy --config trivy.yaml image --skip-dirs '' --platform linux/amd64 --format cyclonedx --output tmp/sbom.cdx.json "$IMAGE"
   ```

1. **Deploy privately**: pass config via `--set-env-vars` (`PORT` is injected by Cloud Run; the Python web starter expects `HOST=0.0.0.0`, `ENVIRONMENT=production`, and `DATABASE_URL`) and pin explicit [secret versions](https://docs.cloud.google.com/run/docs/configuring/services/secrets) rather than `latest` (mount secret volumes only when live rotation without redeploy is required):

   ```bash
   gcloud run deploy <slug> --project=<project> --image="$IMAGE" --region=<region> \
     --service-account="<slug>-runtime@<project>.iam.gserviceaccount.com" \
     --set-env-vars=HOST=0.0.0.0,ENVIRONMENT=production \
     --set-secrets=DATABASE_URL=database-url:<version> \
     --invoker-iam-check --no-allow-unauthenticated
   ```

   Always enforce private invocation as a postcondition (`gcloud` can downgrade failed IAM removals to warnings): run `Verify private invocation` from [deploy.yml](../templates/deploy.yml) with [verify-private.py](../templates/verify-private.py) (`.github/scripts/verify-private.py`) to confirm Invoker IAM is enabled and neither service nor project IAM contains `allUsers` or `allAuthenticatedUsers` (even conditional/custom-role bindings), and verify an unauthenticated HTTP request is rejected.

1. **Seed a runtime secret when authorized**: supply `API_KEY` from the secret store or scoped launcher and validate in memory before piping to `gcloud` so failed pipelines never write empty/multiline secret versions; pin the new version on next deploy.

   ```bash
   (
     set +x
     set -euo pipefail
     : "${API_KEY:?API_KEY must be supplied by the secret store or a scoped launcher}"
     case $API_KEY in *[$'\r\n']*) printf '%s\n' 'API_KEY must be a single-line string.' >&2; exit 1 ;; esac
     printf '%s' "$API_KEY" | gcloud secrets versions add api-key --project="<project>" --data-file=-
   )
   ```

1. **Expose `deploy` as an on-demand task** (never in hooks):

   ```toml
   [tasks.deploy]
   description = "Deploy IMAGE_REF to Cloud Run"
   run = '''
   #!/usr/bin/env bash
   set -euo pipefail
   : "${IMAGE_REF:?Set IMAGE_REF to the reviewed digest reference}"
   [[ "$IMAGE_REF" =~ ^[^[:space:]@]+@sha256:[0-9a-f]{64}$ ]]
   gcloud run deploy <slug> --project <project> --image "$IMAGE_REF" --region <region> --service-account <slug>-runtime@<project>.iam.gserviceaccount.com --invoker-iam-check --no-allow-unauthenticated
   # Then run the private-invocation postcondition from deploy.yml; do not report success without it.
   '''
   ```

1. **Wire CD**: copy [deploy.yml](../templates/deploy.yml) to `.github/workflows/cd.yml` (merge jobs if also using the [github-actions CD template](../../github-actions/references/ci-cd/templates/cd.yml), since WIF pins `cd.yml@`) and stdlib-only [verify-private.py](../templates/verify-private.py) to `.github/scripts/verify-private.py`. Pin `<version>`, configure `GCP_WIF_PROVIDER`, `GCP_DEPLOY_SA`, `GCP_RUNTIME_SA`, `GCP_REGION`, `GCP_ARTIFACT_IMAGE`, `CLOUDRUN_SERVICE`, and `ENABLE_DEPLOY_CLOUDRUN=true`, and keep the uncredentialed `validate` gate ahead of `deploy-cloud-run` ([github-actions](../../github-actions/references/ci-cd/GUIDE.md)).
1. **Roll out through a candidate**: create the service once manually first (`--no-traffic` fails on nonexistent services), keep `gcloud_version` equal to `setup-gcloud` `version`, and define `test:candidate` to probe `/health` and `/ready` on `CANDIDATE_URL` with an invoker ID token (`run.routes.invoke`) before CD runs `update-traffic --to-revisions <revision>=100 --remove-tags candidate` (or strips `candidate` on failure/cancellation).
