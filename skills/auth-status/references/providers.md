# Secondary Provider Auth Probes and Env Overrides

Read-only status checks (check both exit code and parsed fields) and env-var override names.

## Secondary connector probes

| Provider     | Probe                                                                          | Recovery                                                 |
| ------------ | ------------------------------------------------------------------------------ | -------------------------------------------------------- |
| Firebase     | `firebase projects:list --non-interactive --json \| jq '.status'`              | `firebase login` or `dot login gcp` (ADC fallback)       |
| Colab        | `colab --auth adc sessions` (no VM allocated; check stderr)                    | `dot login colab`                                        |
| Hugging Face | `hf auth whoami`                                                               | `hf auth login`                                          |
| Kaggle       | `kaggle competitions list --page-size 1 >/dev/null`                            | `kaggle auth login`                                      |
| AWS SSO      | `aws sts get-caller-identity --profile <profile> --no-cli-pager`               | `aws sso login --profile <profile>`                      |
| Databricks   | `databricks auth profiles`                                                     | `databricks auth login --host <url> --profile <profile>` |
| Atlassian    | `acli auth status` / `acli jira auth status`                                   | `acli auth login`                                        |
| Cloudflare   | `cf -q auth whoami`                                                            | `cf auth login --use-keyring`                            |
| Datadog      | `pup auth status`                                                              | `pup auth login --read-only --site <site>`               |
| SonarQube    | `sonar auth status`                                                            | `sonar auth login`                                       |
| Vault        | `vault status -format=json; vault token lookup -format=json \| jq '.policies'` | `vault login -no-print`                                  |
| Bitwarden    | `bw --nointeraction status \| jq '{status, userEmail}'` (`unlock --check`)     | `bw login` / `bw unlock`                                 |

Notes: `vault status` exits `2` when sealed (distinct from error exit `1`); `bw --nointeraction unlock --check` exits `0` only when the session key is unlocked.

## Env override detection (presence only)

Report only variable names, never values (`gws` also reads ancestor `.env` `GOOGLE_WORKSPACE_CLI_*`):

```bash
for name in GH_TOKEN GITHUB_TOKEN GOOGLE_APPLICATION_CREDENTIALS CLOUDSDK_AUTH_ACCESS_TOKEN_FILE \
  GOOGLE_WORKSPACE_CLI_TOKEN GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE GEMINI_API_KEY GOOGLE_API_KEY \
  FIREBASE_TOKEN HF_TOKEN HF_TOKEN_PATH KAGGLE_API_TOKEN KAGGLE_KEY AWS_PROFILE AWS_ACCESS_KEY_ID \
  AWS_SESSION_TOKEN DATABRICKS_HOST DATABRICKS_TOKEN DATABRICKS_CLIENT_SECRET DD_API_KEY DD_APP_KEY \
  CF_API_TOKEN CLOUDFLARE_API_TOKEN CLOUDFLARE_API_KEY SONAR_TOKEN SONARQUBE_CLI_KEYCHAIN_FILE \
  VAULT_TOKEN BW_SESSION; do
  if [ -n "$(printenv "$name")" ]; then echo "$name is set"; fi
done
```
