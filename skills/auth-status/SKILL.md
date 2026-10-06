---
name: auth-status
description: "Check CLI and ADC logins across providers: expiry, scopes, re-login commands."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/auth-status
  created: "2026-10-04"
  updated: "2026-10-05"
---

# Auth Status

Answer "am I logged in, until when, and what must I run?" with read-only probes, then hand the user the exact interactive command. `dot doctor --deep` owns the workstation probes; this skill adds the remaining connectors, scope coverage, and recovery. [dot-cli authentication](../dot-cli/references/authentication.md) owns login policy, scopes, and account overrides; each connector skill owns its provider's account selection.

## Workflow

1. **Run the workstation probes**: `dot doctor --deep --json` checks GitHub, the gcloud CLI, ADC, and Workspace with bounded probes and never prints tokens. Read only the auth group; `condition` distinguishes `unauthenticated` from `broken` (state unknown) and flags `insecure` when gh keeps its token in plaintext `hosts.yml`.

   ```bash
   dot doctor --deep --json | jq -c '.checks[] | select(.group == "auth") | {name, status, condition, details}'
   ```

1. **Check scope coverage**: compare granted scopes with the configured policy (`dot config show`, keys `auth.github.scopes`, `auth.workspace.scopes`, and `auth.gcp.adc_scopes`). GitHub lists them in `gh auth status --active --hostname github.com` (the token is masked); Workspace in `gws auth status | jq '{user, token_valid, has_refresh_token, scopes}'`. A missing scope needs a new login even when the probe passes.
1. **Probe other named connectors**: only those the task or user names, each read-only with its exit status checked:

   | Provider     | Probe                                                                                       | Recovery                                                 |
   | ------------ | ------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
   | Colab        | `colab --auth adc sessions` (allocates no VM; inspect stderr before trusting an empty list) | `dot login colab`                                        |
   | Hugging Face | `hf auth whoami`                                                                            | `hf auth login`                                          |
   | Kaggle       | `kaggle competitions list --page-size 1 >/dev/null`                                         | `kaggle auth login`                                      |
   | AWS SSO      | `aws sts get-caller-identity --profile <profile> --no-cli-pager`                            | `aws sso login --profile <profile>`                      |
   | Databricks   | `databricks auth profiles` (validates each profile)                                         | `databricks auth login --host <url> --profile <profile>` |
   | Atlassian    | `acli auth status`; API-token Jira: `acli jira auth status`                                 | `acli auth login`                                        |

1. **Report only provider-exposed expiry**: AWS SSO sessions: `jq -r '.expiresAt // empty' ~/.aws/sso/cache/*.json` (never print the file). Google access tokens refresh hourly; `invalid_grant` or "reauthentication" means the refresh token expired or an organization session policy requires login. Hugging Face tokens do not expire unless revoked. Otherwise write "unknown"; never infer expiry from file dates.
1. **Check environment overrides**: environment credentials win over stored logins. Report presence only, never values:

   ```bash
   for name in GH_TOKEN GITHUB_TOKEN GOOGLE_APPLICATION_CREDENTIALS CLOUDSDK_AUTH_ACCESS_TOKEN_FILE \
     GOOGLE_WORKSPACE_CLI_TOKEN GEMINI_API_KEY GOOGLE_API_KEY HF_TOKEN KAGGLE_API_TOKEN \
     AWS_PROFILE AWS_ACCESS_KEY_ID AWS_SESSION_TOKEN DATABRICKS_HOST DATABRICKS_TOKEN DATABRICKS_CLIENT_SECRET; do
     [ -n "$(printenv "$name")" ] && echo "$name is set"
   done
   ```

1. **Report and hand off**: one table of provider, account (no token), status, scopes gap, expiry, and next action. Browser logins are interactive: give each as `! <command>` for the user to run in the session, preferring `dot login all` or `dot login github|workspace|gcp|colab` over native commands. When the user says they logged in, re-run only the failed probes.

## Gotchas

- **Never print secrets**: no `print-access-token`, `hf auth token`, `kaggle auth print-access-token`, `kaggle config view`, `aws configure export-credentials`, or `--show-token` in a transcript; dot's probes capture token output internally.
- **Exit 0 is not proof**: `gh auth status --json` and Colab can succeed while reporting a failure; read the state and stderr.
- **Native ADC logins drop configured scopes**: a native ADC login (`gcloud auth application-default login`, `gcloud auth login --update-adc`) replaces the grant and drops the Colab and BigQuery read-only scopes; `dot login gcp|colab` request `auth.gcp.adc_scopes`, which keeps them. Run `dot login colab` to restore them ([Colab ADC](../dot-cli/references/authentication.md#colab-adc)).
- **Probing is read-only**: logging in, switching accounts, adding scopes, or editing `dot` configuration needs the user.

## Documentation

- [gh auth status](https://cli.github.com/manual/gh_auth_status) · [gcloud auth](https://cloud.google.com/sdk/gcloud/reference/auth) · [AWS SSO](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html)
- Companion skills: [dot-cli](../dot-cli/SKILL.md) (login and setup), [gcloud](../gcloud/SKILL.md), [gh](../gh/SKILL.md), [gws](../gws/SKILL.md), [colab](../colab/SKILL.md).
