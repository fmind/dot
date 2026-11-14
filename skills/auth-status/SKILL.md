---
name: auth-status
description: "Check CLI and ADC logins across providers: expiry, scopes, re-login commands."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/auth-status
  created: "2026-10-04"
  updated: "2026-11-14"
---

# Auth Status

Check login state, scopes, and expiry with read-only probes, then give the user exact interactive re-login commands. `dot doctor --deep` probes core workstation auth; [dot-cli authentication](../dot-cli/references/authentication.md) owns policy and scopes; each connector skill owns account selection.

## Workflow

1. **Run core probes** (`condition` separates `unauthenticated`, `broken`, and plaintext `hosts.yml` `insecure` without exposing tokens):

   ```bash
   dot doctor --deep --json | jq -c '.checks[] | select(.group == "auth") | {name, status, condition, details}'
   ```

1. **Check granted scopes** (`dot config show` keys `auth.{github.scopes,workspace.scopes,gcp.adc_scopes}`): run `gh auth status --active --hostname github.com` and `gws auth status | jq '{user, token_valid, has_refresh_token, scopes}'`. Report missing or excess grants via `dot setup github`, `gh auth refresh -h github.com --remove-scopes <scopes>`, or `dot login workspace --force`.
1. **Probe secondary connectors & env overrides**: run only relevant non-interactive read probes and check presence-only env overrides listed in [providers](references/providers.md).
1. **Report only provider-exposed expiry**: for AWS SSO, read `jq -r 'select(has("accessToken")) | .expiresAt' ~/.aws/sso/cache/*.json`; otherwise report `"unknown"`.
1. **Hand off**: list account, status, scope gaps, expiry, and interactive `! <command>` per provider—preferring `dot login` (`github|workspace|gcp|colab`) over raw native commands so Colab/BigQuery ADC scopes stay intact ([Colab ADC](../dot-cli/references/authentication.md#colab-adc)). Re-probe only failed items.

## Gotchas

- **Never print secrets**: forbid `print-access-token`, `gh auth token`, `gws auth export`, `databricks auth token`, `hf auth token`, `kaggle auth print-access-token`, `kaggle config view`, `aws configure export-credentials`, `vault print token`, `bw get`, `bw unlock --raw`, reading `~/.sonar/sonarqube-cli/tokens.json`, `~/.config/configstore/firebase-tools.json`, or `~/.config/pup/`, dumping Cloudflare config tokens, and `--show-token`.
- **Exit 0 or 2 nuances**: `gh auth status --json` and `colab` can exit 0 on auth failure (inspect JSON/stderr); `vault status -format=json` exits `2` when sealed (not unauthenticated); pass `bw --nointeraction` so Bitwarden never hangs on a TTY prompt.
- **Strictly read-only**: logging in, switching accounts, changing scopes, or editing `dot` config requires user action.

## Documentation

- [Provider probes & env overrides](references/providers.md) · [gh auth status](https://cli.github.com/manual/gh_auth_status) · [gcloud auth](https://docs.cloud.google.com/sdk/gcloud/reference/auth) · [AWS SSO](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html)
- Companion skills: [dot-cli](../dot-cli/SKILL.md), [gcloud](../gcloud/SKILL.md), [gh](../gh/SKILL.md), [gws](../gws/SKILL.md), [colab](../colab/SKILL.md), [pup](../pup/SKILL.md), [cf](../cf/SKILL.md).
