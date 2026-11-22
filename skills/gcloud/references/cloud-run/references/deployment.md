# Cloud Run Deployment Commands

1. **Pin and install image tools**: pin exact stable versions in `mise.toml`, lock, and install before scanning or pushing ([upgrade-tools](../../../../mise/references/upgrade-tools/GUIDE.md) owns upgrades).

   ```bash
   mise use --pin cosign trivy
   mise lock
   mise install --locked cosign trivy
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
   IMAGE_REPOSITORY="<region>-docker.pkg.dev/<project>/<repository>/<slug>"
   TAG="<tag>"
   [[ "$IMAGE_REPOSITORY" =~ ^[^[:space:]@]+$ && "$TAG" =~ ^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$ ]]
   gcloud auth configure-docker "<region>-docker.pkg.dev" --quiet
   mkdir -p tmp
   docker buildx build --platform linux/amd64 --push --tag "$IMAGE_REPOSITORY:$TAG" --metadata-file tmp/image-metadata.json .
   DIGEST="$(jq -er '."containerimage.digest" | select(test("^sha256:[0-9a-f]{64}$"))' tmp/image-metadata.json)"
   IMAGE="$IMAGE_REPOSITORY@$DIGEST"
   ```

1. **Scan, sign, and attest `$IMAGE`**: run the [cosign release sequence](../../../../containers/references/docker/references/cosign.md#release-sequence) (public transparency-log disclosure applies even to private registries):

   ```bash
   trivy --config trivy.yaml image --skip-dirs '' --platform linux/amd64 "$IMAGE"
   trivy --config trivy.yaml image --skip-dirs '' --platform linux/amd64 --format cyclonedx --output tmp/sbom.cdx.json "$IMAGE"
   ```

1. **Deploy privately**: pass `HOST=0.0.0.0`, `ENVIRONMENT=production`, and pinned [secret versions](https://docs.cloud.google.com/run/docs/configuring/services/secrets) (`PORT` is injected by Cloud Run; never `latest`; mount secret volumes only for rotation without redeploy):

   ```bash
   gcloud run deploy <slug> --project=<project> --image="$IMAGE" --region=<region> \
     --service-account="<slug>-runtime@<project>.iam.gserviceaccount.com" \
     --set-env-vars=HOST=0.0.0.0,ENVIRONMENT=production --set-secrets=DATABASE_URL=database-url:<version> \
     --invoker-iam-check --no-allow-unauthenticated
   ```

   Run `Verify private invocation` ([deploy.yml](../templates/deploy.yml) + [verify-private.py](../templates/verify-private.py)) as a postcondition to reject `allUsers`/`allAuthenticatedUsers` bindings (including conditional/custom roles) and confirm unauthenticated requests fail.

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

1. **Expose `deploy` as an on-demand task** (never in hooks): validate `IMAGE_REF` (`^[^[:space:]@]+@sha256:[0-9a-f]{64}$`), deploy `--service-account ... --invoker-iam-check --no-allow-unauthenticated`, and run the private-invocation postcondition before reporting success.

1. **Wire CD**: copy [deploy.yml](../templates/deploy.yml) to `.github/workflows/cd.yml` (merge with [github/ci-cd CD](../../../../github/references/ci-cd/templates/cd.yml) if sharing `cd.yml@`), plus [verify-private.py](../templates/verify-private.py) and [probe-candidate.py](../templates/probe-candidate.py) to `.github/scripts/`. Pin `<version>`, configure the `GCP_*`/`CLOUDRUN_SERVICE`/`ENABLE_DEPLOY_CLOUDRUN=true` vars required by `deploy.yml`, and keep `validate` uncredentialed ([github/ci-cd](../../../../github/references/ci-cd/GUIDE.md)).
1. **Roll out through a candidate**: create the service once manually (`--no-traffic` fails on new services), keep `gcloud_version` equal to `setup-gcloud` `version`, and wire `test:candidate` (`python3 .github/scripts/probe-candidate.py "$CANDIDATE_URL"`) before `update-traffic` promotes the revision.
