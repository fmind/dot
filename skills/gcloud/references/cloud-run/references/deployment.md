# Cloud Run Deployment Commands

1. **Pin and install image tools** in `mise.toml` ([upgrade-tools](../../../../mise/references/upgrade-tools/GUIDE.md)):

   ```bash
   mise use --pin cosign trivy
   mise lock
   mise install --locked cosign trivy
   ```

1. **Validate locally**: target `--platform linux/amd64` in `build:image`, then run `uv sync --locked && mise run all && mise run check:image`.

1. **Build and push after authorization**: capture BuildKit's validated `@sha256:` digest:

   ```bash
   set -euo pipefail
   IMAGE_REPOSITORY="<region>-docker.pkg.dev/<project>/<repository>/<slug>"
   TAG="<tag>"
   [[ "$IMAGE_REPOSITORY" =~ ^[^[:space:]@]+$ && "$TAG" =~ ^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$ ]]
   gcloud auth configure-docker "<region>-docker.pkg.dev" --quiet
   mkdir -p tmp
   docker buildx build --platform linux/amd64 --push --tag "$IMAGE_REPOSITORY:$TAG" --metadata-file tmp/image-metadata.json .
   DIGEST="$(jq -er '."containerimage.digest" | select(test("^sha256:[0-9a-f]{64}$"))' tmp/image-metadata.json)"
   IMAGE="$IMAGE_REPOSITORY@$DIGEST"
   ```

1. **Scan, sign, and attest `$IMAGE`**: run the [cosign release sequence](../../../../containers/references/docker/references/cosign.md#release-sequence) after Trivy scan and SBOM generation:

   ```bash
   trivy --config trivy.yaml image --skip-dirs '' --platform linux/amd64 "$IMAGE"
   trivy --config trivy.yaml image --skip-dirs '' --platform linux/amd64 --format cyclonedx --output tmp/sbom.cdx.json "$IMAGE"
   ```

1. **Deploy privately**: pin [secret versions](https://docs.cloud.google.com/run/docs/configuring/services/secrets) (never `latest`; Cloud Run injects `PORT`):

   ```bash
   gcloud run deploy <slug> --project=<project> --image="$IMAGE" --region=<region> \
     --service-account="<slug>-runtime@<project>.iam.gserviceaccount.com" \
     --set-env-vars=HOST=0.0.0.0,ENVIRONMENT=production --set-secrets=DATABASE_URL=database-url:<version> \
     --invoker-iam-check --no-allow-unauthenticated
   ```

   Verify both privacy postconditions: run `python3 -I .github/scripts/verify-private.py "$RUNNER_TEMP" "$CLOUDRUN_SERVICE"` ([verify-private.py](../templates/verify-private.py)) to confirm `invoker-iam-disabled` is not `"true"` and reject `allUsers`/`allAuthenticatedUsers` in service and project IAM policies (including conditional/custom roles), then run `python3 -I .github/scripts/probe-candidate.py --check-unauth "$CANDIDATE_URL"` ([probe-candidate.py](../templates/probe-candidate.py)) to confirm unauthenticated `GET /health` returns `401`/`403` and authenticated `/health` and `/ready` return `200`.

1. **Seed a runtime secret when authorized**: validate `API_KEY` in memory before piping to `gcloud`; pin the new version on next deploy.

   ```bash
   (
     set +x
     set -euo pipefail
     : "${API_KEY:?API_KEY must be supplied by the secret store or a scoped launcher}"
     case $API_KEY in *[$'\r\n']*) printf '%s\n' 'API_KEY must be a single-line string.' >&2; exit 1 ;; esac
     printf '%s' "$API_KEY" | gcloud secrets versions add api-key --project="<project>" --data-file=-
   )
   ```

1. **Wire on-demand deploy & CD**: keep `deploy` out of hooks (validate `IMAGE_REF` matches `@sha256:[0-9a-f]{64}$`). Copy [deploy.yml](../templates/deploy.yml) to `.github/workflows/cd.yml` (merging with [github/ci-cd CD](../../../../github/references/ci-cd/templates/cd.yml) if sharing `cd.yml@`), plus `verify-private.py` and `probe-candidate.py` to `.github/scripts/`. Create the service once manually (`--no-traffic` fails on new services), set `GCP_*`/`CLOUDRUN_SERVICE`/`ENABLE_DEPLOY_CLOUDRUN=true`, keep `gcloud_version` equal to `setup-gcloud` `version`, and keep `validate` uncredentialed ([github/ci-cd](../../../../github/references/ci-cd/GUIDE.md)).
