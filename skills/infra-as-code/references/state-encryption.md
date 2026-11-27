---
name: state-encryption
description: "Configure OpenTofu client-side state and plan encryption with GCP KMS and migrate plaintext state."
---

# OpenTofu State Encryption

Encrypt state and `.tfplan` files client-side with GCP KMS as sketched in [versions.tf](../templates/versions.tf). Provision the KMS key and verify IAM access for every operator and CI principal before enforcing encryption.

## Workflow

1. **Back up state and provision the KMS key**: lost KMS access makes encrypted state permanently unreadable. Provision a dedicated keyring/key (matching `templates/versions.tf`) outside the encrypted state itself and grant operators + CI `roles/cloudkms.cryptoKeyEncrypterDecrypter`:
   ```bash
   gcloud kms keyrings create tofu --location="<region>" --project="<project-id>"
   gcloud kms keys create state --keyring=tofu --location="<region>" --purpose=encryption --rotation-period=90d --project="<project-id>"
   gcloud kms keys add-iam-policy-binding state --keyring=tofu --location="<region>" --member="serviceAccount:<apply-sa>" --role="roles/cloudkms.cryptoKeyEncrypterDecrypter" --project="<project-id>"
   ```
1. **Enable on fresh state**: uncomment `encryption` with `enforced = true` on `state` and `plan`, then run `tofu init` and a reviewed `plan`.
1. **Migrate existing plaintext state**: add `method "unencrypted" "migrate" {}`, temporarily swap `state` `enforced` for `fallback { method = method.unencrypted.migrate }`, run one authorized `tofu apply -refresh-only` (rewrites state ciphertext without mutating cloud resources), then remove both fallback and `migrate` and restore `enforced = true`.
1. **Verify**: confirm the stored GCS object is ciphertext and `tofu plan` succeeds for operators and CI.

## Gotchas

- **Never rename `key_provider` or `method` labels** after encrypting data, or OpenTofu cannot locate the decryption key.
- **OpenTofu-only**: HashiCorp `terraform` cannot parse `encryption` blocks or encrypted state.

## Documentation

- [State encryption](https://opentofu.org/docs/language/state/encryption/)
