---
name: auth-status
description: "Check CLI and ADC logins across providers: expiry, scopes, re-login commands."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/auth-status
  created: "2026-10-04"
  updated: "2026-11-13"
---

# Auth Status

Check login state, scopes, and expiry with read-only probes, then give the user the exact interactive re-login command. `dot doctor --deep` probes core workstation auth; [dot-cli authentication](../dot-cli/references/authentication.md) owns policy and scopes; each connector skill owns account selection.

## Workflow

1. **Run core probes** (`condition` separates `unauthenticated`, `broken`, and plaintext `hosts.yml` `insecure` without exposing tokens):

   ```bash
   dot doctor --deep --json | jq -c '.checks[] | select(.group == "auth") | {name, status, condition, details}'
   ```

1. **Check granted scopes** (`dot config show` keys `auth.{github.scopes,workspace.scopes,gcp.adc_scopes}`): run `gh auth status --active --hostname github.com` and `gws auth status | jq '{user, token_valid, has_refresh_token, scopes}'`. Report missing or excess grants via `dot setup github`, `gh auth refresh -h github.com --remove-scopes <scopes>`, or `dot login workspace --force`.
1. **Probe other connectors** (checking both exit code and output):

   | Provider     | Probe                                                             | Recovery                                                 |
   | ------------ | ----------------------------------------------------------------- | -------------------------------------------------------- |
   | Colab        | `colab --auth adc sessions` (no VM allocated; check stderr)       | `dot login colab`                                        |
   | Hugging Face | `hf auth whoami`                                                  | `hf auth login`                                          |
   | Kaggle       | `kaggle competitions list --page-size 1 >/dev/null`               | `kaggle auth login`                                      |
   | AWS SSO      | `aws sts get-caller-identity --profile <profile> --no-cli-pager`  | `aws sso login --profile <profile>`                      |
   | Databricks   | `databricks auth profiles`                                        | `databricks auth login --host <url> --profile <profile>` |
   | Atlassian    | `acli auth status` / `acli jira auth status`                      | `acli auth login`                                        |
   | Cloudflare   | `cf -q auth whoami`                                               | `cf auth login`                                          |
   | Datadog      | `pup auth status`                                                 | `pup auth login --read-only --site <site>`               |
   | SonarQube    | `sonar auth status`                                               | `sonar auth login`                                       |
   | Vault        | `vault token lookup -format=json \| jq '{expire_time, policies}'` | `vault login`                                            |
   | Bitwarden    | `bw status \| jq '{status, userEmail}'`                           | `bw login` / `bw unlock`                                 |

1. **Report only provider-exposed expiry**: for AWS SSO, read `jq -r 'select(has("accessToken")) | .expiresAt' ~/.aws/sso/cache/*.json`; otherwise report `"unknown"`.
1. **Detect env overrides** (presence only, never values; note `gws` reads ancestor `.env` `GOOGLE_WORKSPACE_CLI_*`):

   ```bash
   for name in GH_TOKEN GITHUB_TOKEN GOOGLE_APPLICATION_CREDENTIALS CLOUDSDK_AUTH_ACCESS_TOKEN_FILE \
     GOOGLE_WORKSPACE_CLI_TOKEN GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE GEMINI_API_KEY GOOGLE_API_KEY \
     HF_TOKEN KAGGLE_API_TOKEN KAGGLE_KEY AWS_PROFILE AWS_ACCESS_KEY_ID AWS_SESSION_TOKEN \
     DATABRICKS_HOST DATABRICKS_TOKEN DATABRICKS_CLIENT_SECRET DD_API_KEY DD_APP_KEY \
     CLOUDFLARE_API_TOKEN CLOUDFLARE_API_KEY SONAR_TOKEN VAULT_TOKEN BW_SESSION; do
     if [ -n "$(printenv "$name")" ]; then echo "$name is set"; fi
   done
   ```

1. **Hand off**: list account, status, scope gaps, expiry, and interactive `! <command>` per provider—preferring `dot login` (`github|workspace|gcp|colab`) over raw native commands so Colab/BigQuery ADC scopes stay intact ([Colab ADC](../dot-cli/references/authentication.md#colab-adc)). Re-probe only failed items.

## Gotchas

- **Never print secrets**: forbid `print-access-token`, `gh auth token`, `gws auth export`, `databricks auth token`, `hf auth token`, `kaggle auth print-access-token`, `kaggle config view`, `aws configure export-credentials`, `vault print token`, `bw get`, `bw unlock --raw`, reading `~/.sonar/sonarqube-cli/tokens.json` or `~/.config/pup/`, dumping Cloudflare config tokens, and `--show-token`.
- **Exit 0 is not proof**: `gh auth status --json` and `colab` can exit 0 on auth failure—inspect JSON fields and stderr.
- **Strictly read-only**: logging in, switching accounts, changing scopes, or editing `dot` config requires user action.

## Documentation

- [gh auth status](https://cli.github.com/manual/gh_auth_status) · [gcloud auth](https://docs.cloud.google.com/sdk/gcloud/reference/auth) · [AWS SSO](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html)
- Companion skills: [dot-cli](../dot-cli/SKILL.md) (login and setup), [gcloud](../gcloud/SKILL.md), [gh](../gh/SKILL.md), [gws](../gws/SKILL.md), [colab](../colab/SKILL.md), [pup](../pup/SKILL.md), [cf](../cf/SKILL.md).
