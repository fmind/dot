---
name: authentication
description: "Reconcile configured provider logins, OAuth scopes, one-off grants, and scoped secrets."
---

# Workstation Authentication

[README](https://github.com/fmind/dot#authentication--logins) lists commands and `dot login --help` owns flags; [auth-status](auth-status/GUIDE.md) owns cross-provider probes, expiry, and scopes.

- **Fixed order**: `dot login` runs `auth.login` (default `[github, gcp, workspace]`) in order GitHub → GCP + ADC → Workspace, skipping ready steps and failing closed on unknown state.
- **Preflight & OAuth**: readiness probes run first in memory (`--check` skips browsers, rejects `--grant`/`--project`/`--setup`, and fails when granted tokens hold forbidden or excess scopes); missing logins open browser OAuth (copying GitHub device codes) without printing secrets. On GCE VMs, probes ignore metadata service accounts (`*.gserviceaccount.com`) and require user ADC; over headless SSH, `gcp` passes `--no-launch-browser` and `workspace` prints a localhost `curl` callback hint.
- **Precedence & `--setup`**: Workspace project resolves CLI arg → `GWS_PROJECT` → `auth.workspace.project` in `~/.config/dot.yaml`. When an existing OAuth client belongs to a different or unreported project (for example under `GOOGLE_WORKSPACE_CLI_CONFIG_DIR`), `dot login` fails closed instead of running `gws auth setup`; unset the profile override, run `dot login workspace --project <id>`, or pass `--setup` (`dot login workspace --setup`) to reconfigure or enable APIs, then re-run `dot login` after config changes.
- **Plaintext `hosts.yml` warning**: if `gh` fell back to insecure `hosts.yml`, unlock macOS Keychain or Linux Secret Service (`login` / `default`), then run `gh auth logout && dot login github`.

## Workspace scopes & one-off grants

- **50-scope hard limit**: Google's consent screen hangs above 50 scopes; `dot login workspace` bundles the collaboration, Apps Script, and Pub/Sub scopes in [`policy.yaml`](https://github.com/fmind/dot/blob/main/dot/src/fmind_dot/policy.yaml) and refuses >50 total.
- **`auth.workspace.extra_scopes`**: because `gws` replaces its grant on login, `extra_scopes` appends to the bundled Workspace scopes up to 50.
- **Temporary `--grant`**: pass `--grant <scope>` for one task, then revert (`dot login workspace --force` or `dot login github`).
- **Safe one-offs**: GitHub `write:ssh_signing_key`, `write:packages`, `write:org`; Workspace Admin Directory, Chrome, Vault, Analytics.
- **Forbidden scopes**: [`policy.yaml`](https://github.com/fmind/dot/blob/main/dot/src/fmind_dot/policy.yaml) blocks enterprise-admin GitHub scopes and overly broad or incompatible Workspace scopes (such as `https://mail.google.com/` and `cloud-platform`, which `gcloud` IAM owns) across config, `--grant`, and readiness checks.

## GCP ADC

`dot login gcp` requests `gcp.adc_scope_suffixes` from [`policy.yaml`](https://github.com/fmind/dot/blob/main/dot/src/fmind_dot/policy.yaml) so BigQuery, Cloud SQL, and logging scopes stay bundled. Because ADC overwrites its grant on login, keep scopes intact via `dot login gcp`:

```bash
dot login gcp --check                    # probe gcloud + bundled ADC scopes safely
dot login gcp                            # re-grant full bundled ADC scope set
```

Unset `GOOGLE_APPLICATION_CREDENTIALS` before updating ADC, and rerun `dot login gcp --force` if `gcloud auth login --update-adc` overwrites scopes.

## Customer overrides and isolation

- **Hugging Face**: `HF_TOKEN` overrides the stored token file; `HF_TOKEN_PATH` selects an alternate file. For strict multi-tenant isolation, use a separate OS user, container, or `$HOME`.

## Scoped credentials

- **`with-secret NAME [--] COMMAND ...`**: reads `NAME` from env first, else a non-symlink `0600`/`0400` file (`<= 64 KiB`, `O_NOFOLLOW` in `0700` `~/.config/dot/secrets/`) and runs `execve` with `NAME` only in child env (zero `argv` exposure; no personal fallback).
- **Vault, Bitwarden & SonarQube**: pass `vault login -` and `bw` secrets via stdin or `with-secret`, never `argv` or global env; SonarQube stores tokens in `~/.sonar/sonarqube-cli/tokens.json` (`0600` via `SONARQUBE_CLI_KEYCHAIN_FILE`).
- **Managed vs retired keys**: store only keys that still lack OAuth/ADC or Trusted Publishing (e.g., read-only `OPENROUTER_MANAGEMENT_KEY`); `with-secret` rejects `UV_PUBLISH_TOKEN` (PyPI uses Trusted Publishing).
