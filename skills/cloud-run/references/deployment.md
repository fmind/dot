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

1. **Validate locally**: run the Python project's complete gate and scan the local image archive before any registry write.

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
   docker buildx build --push --tag "$IMAGE_REPOSITORY:$TAG" --metadata-file tmp/image-metadata.json .
   DIGEST="$(jq -er '."containerimage.digest" | select(test("^sha256:[0-9a-f]{64}$"))' tmp/image-metadata.json)"
   IMAGE="$IMAGE_REPOSITORY@$DIGEST"
   printf '%s\n' "$IMAGE" >tmp/image-ref.txt
   ```

1. **Scan, sign, and attest the same digest**: stop on any scan or verification failure. Replace the certificate identity with the authorized workflow or developer identity.

   ```bash
   trivy --config trivy.yaml image "$IMAGE"
   trivy --config trivy.yaml image --format cyclonedx --output tmp/sbom.cdx.json "$IMAGE"
   cosign sign --yes "$IMAGE"
   cosign verify --certificate-identity '<identity>' --certificate-oidc-issuer '<issuer>' "$IMAGE"
   cosign attest --yes --type cyclonedx --predicate tmp/sbom.cdx.json "$IMAGE"
   cosign verify-attestation --type cyclonedx --certificate-identity '<identity>' --certificate-oidc-issuer '<issuer>' "$IMAGE"
   ```

1. **Deploy privately**: plain configuration uses `--set-env-vars`; secrets use Secret Manager references so values never enter the image or command history.

   ```bash
   gcloud run deploy <slug> --image="$IMAGE" --region=<region> \
     --service-account="<slug>-runtime@<project>.iam.gserviceaccount.com" \
     --set-env-vars=LOG_LEVEL=info \
     --set-secrets=API_KEY=api-key:latest \
     --no-allow-unauthenticated
   ```

1. **Seed a runtime secret when authorized**: decrypt only into the pipe; do not write plaintext to disk.

   ```bash
   sops -d secrets.enc.yaml | yq -r .api_key | gcloud secrets versions add api-key --data-file=-
   ```

1. **Expose deployment as an on-demand task**: keep it out of hooks because it mutates a live service and can spend money.

   ```toml
   [tasks.deploy]
   description = "Deploy IMAGE_REF to Cloud Run"
   run = '''
   : "${IMAGE_REF:?Set IMAGE_REF to the reviewed digest reference}"
   [[ "$IMAGE_REF" =~ ^[^[:space:]@]+@sha256:[0-9a-f]{64}$ ]]
   gcloud run deploy <slug> --image "$IMAGE_REF" --region <region> --service-account <slug>-runtime@<project>.iam.gserviceaccount.com --no-allow-unauthenticated
   '''
   ```

1. **Wire CD**: adapt [deploy.yml](deploy.yml), set `GCP_WIF_PROVIDER`, `GCP_DEPLOY_SA`, `GCP_RUNTIME_SA`, `GCP_REGION`, `GCP_ARTIFACT_IMAGE`, and `CLOUDRUN_SERVICE`, then set `ENABLE_DEPLOY_CLOUDRUN=true`.
