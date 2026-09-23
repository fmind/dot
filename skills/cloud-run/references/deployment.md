# Cloud Run Deployment Commands

1. **Pin and install image tools**: add exact stable versions to the Python project's `mise.toml`, generate its lock entries, and install them before any image scan or registry write. Upgrade both pins deliberately through [upgrade-tools](../../upgrade-tools/SKILL.md).

   ```toml
   [tools]
   cosign = "3.1.3"
   trivy = "0.74.0"
   ```

   ```bash
   mise lock
   mise install --locked cosign trivy
   cosign version
   trivy --version
   ```

1. **Validate locally**: set the Cloud Run project's `build:image` task to `--platform linux/amd64`, including on ARM development hosts, then run its complete gate and scan the local image archive before any registry write.

   ```bash
   uv sync --locked
   mise run all
   mise run check:image
   ```

1. **Build and push after authorization**: use the full Artifact Registry image repository without a tag in `IMAGE_REPOSITORY`. BuildKit writes the registry digest to metadata; validate it before creating the deployable reference.

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

1. **Scan, sign, and attest the same digest**: stop on any scan or verification failure. Public Sigstore discloses permanent signing identity and digest metadata even for a private image; include this in publication authority per [Cosign](../../containerize/references/cosign.md). Replace the certificate identity with the authorized workflow or developer identity.

   ```bash
   trivy --config trivy.yaml image --skip-dirs '' --platform linux/amd64 "$IMAGE"
   trivy --config trivy.yaml image --skip-dirs '' --platform linux/amd64 --format cyclonedx --output tmp/sbom.cdx.json "$IMAGE"
   cosign sign --yes "$IMAGE"
   cosign verify --certificate-identity '<identity>' --certificate-oidc-issuer '<issuer>' "$IMAGE"
   cosign attest --yes --type cyclonedx --predicate tmp/sbom.cdx.json "$IMAGE"
   cosign verify-attestation --type cyclonedx --certificate-identity '<identity>' --certificate-oidc-issuer '<issuer>' "$IMAGE"
   ```

1. **Deploy privately**: plain configuration uses `--set-env-vars`; secrets use Secret Manager references so values never enter the image or command history. The Python web starter requires `HOST=0.0.0.0`, `ENVIRONMENT=production`, and a `DATABASE_URL` secret accessible to its runtime identity. Adapt these names to the application; Cloud Run supplies `PORT`.

   ```bash
   gcloud run deploy <slug> --image="$IMAGE" --region=<region> \
     --service-account="<slug>-runtime@<project>.iam.gserviceaccount.com" \
     --set-env-vars=HOST=0.0.0.0,ENVIRONMENT=production,LOG_LEVEL=info \
     --set-secrets=DATABASE_URL=database-url:latest,API_KEY=api-key:latest \
     --invoker-iam-check --no-allow-unauthenticated
   ```

   Treat private invocation as a postcondition, not a successful deploy exit code. Run the `Verify private invocation` checks in [deploy.yml](../templates/deploy.yml) after imperative or declarative deployment, using [verify-private.py](../templates/verify-private.py) at `.github/scripts/verify-private.py`: the Invoker IAM check must be enabled, and service/project IAM policies must contain neither `allUsers` nor `allAuthenticatedUsers`. Reject those principals even in conditional bindings or custom roles. A failed policy read, unknown setting, or remaining grant fails verification; gcloud can otherwise turn a failed IAM removal into a warning. Resolve inherited organization/folder access during bootstrap; these service/project checks are not a general IAM policy evaluator. Verify an unauthenticated request is denied before exposing sensitive traffic.

1. **Seed a runtime secret when authorized**: decrypt only into the pipe; do not write plaintext to disk.

   ```bash
   sops -d secrets.enc.yaml | yq -r .api_key | gcloud secrets versions add api-key --data-file=-
   ```

1. **Expose deployment as an on-demand task**: keep it out of hooks because it mutates a live service and can spend money.

   ```toml
   [tasks.deploy]
   description = "Deploy IMAGE_REF to Cloud Run"
   run = '''
   #!/usr/bin/env bash
   set -euo pipefail
   : "${IMAGE_REF:?Set IMAGE_REF to the reviewed digest reference}"
   [[ "$IMAGE_REF" =~ ^[^[:space:]@]+@sha256:[0-9a-f]{64}$ ]]
   gcloud run deploy <slug> --image "$IMAGE_REF" --region <region> --service-account <slug>-runtime@<project>.iam.gserviceaccount.com --invoker-iam-check --no-allow-unauthenticated
   # Then run the private-invocation postcondition from deploy.yml; do not report success without it.
   '''
   ```

1. **Wire CD**: copy [deploy.yml](../templates/deploy.yml) to `.github/workflows/cd.yml` and [verify-private.py](../templates/verify-private.py) to `.github/scripts/verify-private.py`; commit both. The helper uses only Python's standard library. Set `GCP_WIF_PROVIDER`, `GCP_DEPLOY_SA`, `GCP_RUNTIME_SA`, `GCP_REGION`, `GCP_ARTIFACT_IMAGE`, and `CLOUDRUN_SERVICE`, then set `ENABLE_DEPLOY_CLOUDRUN=true`. Preserve its read-only `mise run all` gate and clean-tree check on the tagged revision; the cloud job must depend on their success.
