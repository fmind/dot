# sops integrations

CI decryption and runtime wiring for consumers of sops-encrypted files; the daily workflow stays in [SKILL.md](../SKILL.md).

## CI

Jobs wrap commands in `sops exec-env`, and every other secret rides encrypted in the repo. The simplest decryption path stores an age private key as the single `SOPS_AGE_KEY` GitHub Actions secret, but that long-lived key decrypts every file it is a recipient of. For GCP projects, prefer a `gcp_kms` recipient that CI decrypts through Workload Identity Federation (Application Default Credentials from `google-github-actions/auth`, with `roles/cloudkms.cryptoKeyDecrypter` on that key only), and keep age recipients for humans; retire a former CI age recipient through the [rotation](key-lifecycle.md) sequence.

## Kubernetes (Flux)

1. Commit `*.enc.yaml` manifests encrypted with the `encrypted_regex: ^(data|stringData)$` rule from [sops.yaml](../templates/sops.yaml), so only the secret payload is ciphertext and the manifest stays diffable.
1. Resolve the intended cluster and authorize transferring the private decryption key before creating the cluster-side secret. Preserve an existing secret; for a new one use `kubectl --context <context> create secret generic sops-age --namespace=flux-system --from-file=age.agekey=<key-file>`. The stored key name must end in `.agekey`; the local key file can retain its existing name and location. Inspect metadata only when verifying the secret, and check Flux reconciliation without printing decrypted values.
1. Point the Kustomization at it with `spec.decryption: {provider: sops, secretRef: {name: sops-age}}`; Flux decrypts in-cluster.

## OpenTofu

[infra-as-code](../../infra-as-code/SKILL.md) owns `TF_VAR_<name>` delivery through `sops exec-env`, ephemeral inputs, and state encryption.

## Runtime services

sops secures secrets in git; long-running workloads read from a runtime manager (Secret Manager via [cloud-run](../../cloud-run/SKILL.md), or Vault when dynamic credentials are required), and sops guards only the bootstrap material.

## Documentation

- [Flux sops guide](https://fluxcd.io/flux/guides/mozilla-sops/)
