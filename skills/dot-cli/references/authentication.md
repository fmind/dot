---
name: authentication
description: "Reconcile configured provider logins, OAuth scopes, one-off grants, and scoped secrets."
---

# Workstation Authentication

[README](https://github.com/fmind/dot#authentication--logins) lists commands and `dot login --help` owns flags; [auth-status](../../auth-status/SKILL.md) owns cross-provider probes, expiry, and scopes.

- **Fixed reconciliation order**: `dot login` runs `auth.login` (default `[github, gcp, workspace]`) in order GitHub → GCP + ADC → Workspace → Colab, skipping ready steps, opening OAuth flows in the browser (copying GitHub device codes to the clipboard), and failing closed on unknown state without printing secrets.
- **Concurrent preflight**: readiness probes run first in memory; `dot login --check` validates configured providers (and forbidden GitHub/Workspace grants) without opening a browser.
- **Precedence & config**: Workspace project resolves CLI arg → `GWS_PROJECT` → `auth.workspace.project` in `~/.config/dot.yaml` (`auth.workspace.extra_scopes` extends bundled Workspace scopes, maps merge). Routine logins skip GCP API mutation once the OAuth client is configured; pass `--setup` (`dot login workspace --setup`) to enable APIs or bootstrap a new project. Changing config never updates issued tokens: re-run `dot login`.
- **Plaintext `hosts.yml` warning**: if `gh` fell back to insecure `hosts.yml`, unlock macOS Keychain or Linux Secret Service (collection `login` / `default`), then run `gh auth logout && dot login github`.

## Workspace scopes & one-off grants

- **50-scope hard limit**: Google's consent screen hangs above 50 scopes (`dot login workspace` defaults to 35 universal collaboration, Apps Script, and Pub/Sub scopes and refuses >50). Because `gws` replaces its full grant on login, `auth.workspace.extra_scopes` adds to the 35 bundled scopes up to that ceiling (for example `analytics.readonly`, `webmasters.readonly`, `postmaster.traffic.readonly`, `youtube.readonly`, and `yt-analytics.readonly` on personal creator accounts for 40/50 slots).
- **Temporary `--grant`**: request `--grant <scope>` only for a specific task and revert right after (`dot login workspace --force` or `dot login github`; `repo`, `read:org`, and `gist` are `gh`'s minimum).
- **Safe one-offs**: GitHub key/package/org write scopes (`write:ssh_signing_key`, `write:packages`, `write:org`); Workspace Admin Directory/Chrome/Vault/Analytics scopes.
- **Never request**: GitHub `admin:enterprise`, `manage_runners:enterprise`, `manage_billing:enterprise`; Gmail `https://mail.google.com/` or `gmail.settings.sharing`; Workspace `cloud-platform` (owned by `gcloud` IAM), `apps.alerts`, `chat.app.*`, `chat.import`, `youtubepartner*`, Classroom, or Brand-Account YouTube scopes outside the OAuth org (`policy.yaml` blocks the enterprise-admin, full-mailbox, mail-forwarding, and `cloud-platform` scopes in config, `--grant`, and readiness checks).

## Colab ADC

`dot login gcp` and `dot login colab` share bundled `gcp.adc_scope_suffixes` from [`policy.yaml`](https://github.com/fmind/dot/blob/main/dot/src/fmind_dot/policy.yaml) (ADC overwrites its full grant on every login, so keep `gcloud` + `colaboratory` + read-only sensor scopes together):

```bash
dot login colab --check                  # probe ADC + Colab scopes safely (never run print-access-token)
dot login colab                          # re-grant full bundled ADC scope set for GCP + Colab
colab --auth=adc sessions
```

Check `colab` stderr (it can exit `0` on ADC failure), unset `GOOGLE_APPLICATION_CREDENTIALS` before updating stored ADC, and rerun `dot login colab` if `gcloud auth login --update-adc` overwrites scopes.

## Customer overrides and isolation

- **Hugging Face**: `HF_TOKEN` overrides the stored token file; `HF_TOKEN_PATH` selects an alternate file.
- **Kaggle**: personal access-token files override legacy keys (`KAGGLE_CONFIG_DIR` does not move it); export `KAGGLE_API_TOKEN` for customer accounts.
- **OpenCode**: set `provider.openrouter.options.apiKey` to an env/file ref or isolate `XDG_DATA_HOME`. For strict multi-tenant isolation, use a separate OS user, container, or dedicated `$HOME`.

## Scoped credentials

- **`with-secret NAME [--] COMMAND ...`**: reads `NAME` from env first, else opens a non-symlink `0600`/`0400` regular file (`<= 64 KiB`, `O_NOFOLLOW` inside `0700` `~/.config/dot/secrets/`) and runs `execve` with `NAME` only in child env (zero `argv` exposure; works across shells and nested calls; never auto-falls back to personal credentials).
- **Managed vs retired keys & Vault/Bitwarden**: only read-only `OPENROUTER_MANAGEMENT_KEY` is stored for `with-secret`; SonarQube keeps tokens in `~/.sonar/sonarqube-cli/tokens.json` (`0600` via `SONARQUBE_CLI_KEYCHAIN_FILE`). Feed HashiCorp `vault` and Bitwarden `bw` secrets via stdin (`vault login -`, `bw` stdin) or `with-secret`, never CLI argv or global env exports. `ANTIGRAVITY_SDK_API_KEY`, `JULES_API_KEY`, `STITCH_ACCESS_TOKEN`, `UV_PUBLISH_TOKEN` (PyPI uses CI Trusted Publishing, and `with-secret` rejects it), and `VERTEX_API_KEY` are retired.
