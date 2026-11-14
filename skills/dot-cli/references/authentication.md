---
name: authentication
description: "Reconcile configured provider logins, OAuth scopes, one-off grants, and scoped secrets."
---

# Workstation Authentication

[README](https://github.com/fmind/dot#authentication--logins) lists commands and `dot login --help` owns flags; [auth-status](../../auth-status/SKILL.md) owns cross-provider probes, expiry, and scopes.

- **Fixed reconciliation order**: `dot login` runs `auth.login` (default `[github, gcp, workspace]`) in order `setup github` → GCP + ADC → Workspace setup → Workspace login → Colab, skipping ready steps and failing closed on unknown state without printing secrets.
- **Concurrent preflight**: readiness probes run first in memory; `dot login --check` validates configured providers (and removed GitHub grants) without opening a browser.
- **Precedence & config**: Workspace project resolves CLI arg → `GWS_PROJECT` → `auth.workspace.project` (`dot config show` / `edit`; lists replace defaults, maps merge). Changing config never updates issued tokens — re-run login/setup.
- **Plaintext `hosts.yml` warning**: if `gh` fell back to insecure `hosts.yml`, unlock macOS Keychain or Linux Secret Service (collection `login` / `default`), then run `gh auth logout && dot setup github`.

## Workspace scopes & one-off grants

- **50-scope hard limit**: Google's consent screen hangs above 50 scopes (`dot login workspace` defaults to 48 and refuses >50). Because `gws` replaces its full grant on login, custom `auth.workspace.scopes` must include needed read + write scopes.
- **Temporary `--grant`**: request `--grant <scope>` only for a specific task and revert right after (`dot login workspace --force` or `dot setup github`; `repo`, `read:org`, and `gist` are `gh`'s minimum).
- **Safe one-offs**: GitHub key/package/repo/org write scopes; Workspace Admin Directory/Chrome/Chat/Vault/Analytics/Apps Script scopes.
- **Never request**: GitHub `admin:enterprise`, `manage_runners:enterprise`, `manage_billing:enterprise`; Gmail `https://mail.google.com/` or `gmail.settings.sharing`; Workspace `cloud-platform` (owned by `gcloud` IAM), `apps.alerts`, `chat.app.*`, `chat.import`, `youtubepartner*`, Classroom, or Brand-Account YouTube scopes outside the OAuth org.

## Colab ADC

`dot login gcp` and `dot login colab` share `auth.gcp.adc_scopes` (ADC overwrites its full grant on every login, so keep `gcloud` + `colaboratory` + read-only sensor scopes together):

```bash
dot login colab --check                  # probe ADC + Colab scopes safely (never run print-access-token)
gcloud auth application-default login --scopes=<auth.gcp.adc_scopes>
colab --auth=adc sessions
```

Check `colab` stderr (it can exit `0` on ADC failure), unset `GOOGLE_APPLICATION_CREDENTIALS` before updating stored ADC, and rerun `dot login colab` if `gcloud auth login --update-adc` overwrites scopes.

## Customer overrides and isolation

- **Hugging Face**: `HF_TOKEN` overrides the stored token file; `HF_TOKEN_PATH` selects an alternate file.
- **Kaggle**: personal access-token files override legacy keys (`KAGGLE_CONFIG_DIR` does not move it); export `KAGGLE_API_TOKEN` for customer accounts.
- **OpenCode**: set `provider.openrouter.options.apiKey` to an env/file ref or isolate `XDG_DATA_HOME`. For strict multi-tenant isolation, use a separate OS user, container, or dedicated `$HOME`.

## Scoped credentials

- **`dot secret run NAME -- COMMAND ...`**: reads `NAME` from env first, else `~/.config/dot/secrets/NAME` (`0600`), failing before `exec` on empty, missing, or loose-mode files (child process only; nest calls for multiple keys; never auto-falls back to personal credentials).
- **Managed vs retired keys & Vault/Bitwarden**: only read-only `OPENROUTER_MANAGEMENT_KEY` is stored for `dot secret run`; SonarQube keeps tokens in `~/.sonar/sonarqube-cli/tokens.json` (`0600` via `SONARQUBE_CLI_KEYCHAIN_FILE`). Feed HashiCorp `vault` and Bitwarden `bw` secrets via stdin (`vault login -`, `bw` stdin) or `dot secret run`, never CLI argv or global env exports. `ANTIGRAVITY_SDK_API_KEY`, `JULES_API_KEY`, `STITCH_ACCESS_TOKEN`, `UV_PUBLISH_TOKEN` (PyPI uses CI Trusted Publishing), and `VERTEX_API_KEY` are retired.
