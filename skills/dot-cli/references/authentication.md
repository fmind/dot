---
name: authentication
description: "Reconcile configured provider logins, OAuth scopes, one-off grants, and scoped secrets."
---

# Workstation Authentication

The [README](https://github.com/fmind/dot#authentication--logins) lists login commands and `dot login --help` owns flags; this guide owns policy. For read-only cross-provider login, expiry, and scope sweeps (including HF, Kaggle, AWS, Databricks, and Atlassian), use [auth-status](../../auth-status/SKILL.md).

- **Fixed order**: bare `dot login` reconciles `auth.login` (default `[github, gcp, workspace]`; add `colab` per machine in unmanaged config) in a fixed order regardless of list order: `setup github` → GCP + ADC (Workspace setup manages APIs via `gcloud`; Colab shares ADC) → Workspace setup (when `GWS_PROJECT` or `auth.workspace.project` is set) → Workspace login → Colab, skipping ready steps and stopping on failure.
- **Probe before any browser**: distinct readiness probes run concurrently first and stay cached in memory until login/setup mutates state; login skips only when valid credentials cover requested scopes. `dot login --check` (or `dot login <provider> --check`) checks `auth.login` providers, including removed GitHub grants, without opening a browser.
- **Fail closed**: unknown status fails with recovery guidance instead of starting auth; repair or unset env-token overrides blocking OAuth updates. Failed probes print no tokens or payloads, and Dot caches no credentials.
- **Interactive steps**: GitHub uses the web flow with `gh`'s `git_protocol` (leaving only SSH-key choice and Enter-to-open). `gws` prints its OAuth URL, which `dot` opens via `$BROWSER` (`open` on macOS); over SSH or headless, open the URL manually.
- **GCP**: CLI (`gcloud auth login`) and ADC (`gcloud auth application-default login --scopes=<auth.gcp.adc_scopes>`) check and re-authenticate separately without enforcing one identity; requesting a scoped token proves the ADC grant because Google rejects ungranted scopes.
- **Workspace setup**: reads enabled APIs from `gws auth status` on the configured project (`gcloud services list` on another), enables only missing configured APIs, and skips OAuth client setup when a readable client config exists.

Workspace project precedence: setup argument → `GWS_PROJECT` → `auth.workspace.project`. GitHub targets `github.com`. Inspect/edit policy via `dot config show` and `dot config edit` (`auth.github.scopes`, `auth.github.remove_scopes`, `auth.workspace.scopes`, `auth.workspace.apis`, `auth.gcp.adc_scopes`, `auth.login`); maps merge with defaults while lists replace defaults.

**Workspace scope limit:** Google's consent page hangs after Allow above 50 scopes (45, 47, and 50 succeeded; 52+ hung, bisected 2026-10-26). The 48 defaults leave 2 one-off slots, and `dot login workspace` refuses >50 before opening a browser. Defaults hold everyday writes plus only the read-only scopes narrowed by brain sensors and google CLI (writes already allow reads; GitHub drops implied reads automatically and adds Projects, profile, and org audit-log reads to repo, workflow, gist, and notification access). Workspace writes cover Gmail (`gmail.modify`, basic settings), Drive, Docs, Sheets, Slides, Forms, Calendar, Contacts, Chat messages/spaces, Tasks, Apps Script projects, Analytics (`analytics.edit`, `analytics.manage.users`), Search Console (`webmasters`), and Business Profile. Read-only scopes cover Gmail, Postmaster Tools, Drive, Docs, Calendar, Contacts, Tasks, Chat, Meet, Forms responses, Analytics, Search Console, YouTube and YouTube Analytics, Admin Directory, audit/usage reports, and Chrome policies/reports. `gws` replaces its whole grant on login, so custom `auth.workspace.scopes` must keep them; new Workspace APIs also need `dot setup workspace`.

**One-off grants:** when a command fails for a missing scope, ask the user to run `--grant`, complete the task, then ask them to revert. `dot login workspace --grant SCOPE` (URL or short name like `admin.directory.user.security`) adds a scope once; later `dot login workspace` reports extras, and `dot login workspace --force` restores the configured grant, clearing the wider refresh and cached access tokens. `dot login github --grant SCOPE` adds one; `dot setup github` (or bare `dot login`) removes `auth.github.remove_scopes` entries and prints the removal command for scopes outside that list (`repo`, `read:org`, and `gist` are `gh`'s non-removable minimum).

Possible one-off grants ([GitHub scopes](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps), [Google scopes](https://developers.google.com/identity/protocols/oauth2/scopes)) — grant narrowly and revert immediately after the task:

- **GitHub**: key uploads (`write:{public,ssh_signing,gpg}_key`), package/repo/org writes (`write:packages`, `delete:packages`, `delete_repo`, `write:org`, `admin:org`, `admin:org_hook`, billable `codespace`).
- **Google Workspace**: Admin Directory/Chrome/Chat/Cloud Identity/Vault (`admin.directory.*`, `admin.chrome.printers`, `admin.datatransfer`, `apps.{licensing,groups.settings}`, `chrome.management.*`, `chat.admin.*`, `cloud-identity.*`, `drive.admin.labels`, `ediscovery*`) and extra Tag Manager, Analytics, Postmaster, Chat, Meet, Apps Script, Cloud Support, People, or Keep scopes.

Never request (`--grant` checks only scope shape):

- **GitHub**: enterprise scopes (`admin:enterprise`, `manage_runners:enterprise`, `manage_billing:enterprise`).
- **Gmail**: `https://mail.google.com/` (permanent deletion) and `gmail.settings.sharing` (forwarding/delegates exfiltration).
- **Through gws**: `cloud-platform` (owned by `gcloud` and IAM).
- **YouTube writes through gws**: `youtube`, `youtube.upload`, `youtube.force-ssl` do nothing when a Brand Account sits outside the org `gws`'s OAuth client restricts to; use a separate OAuth grant scoped to the channel owner instead.
- **Not applicable**: `apps.alerts` (`invalid_scope` for users; Alert Center requires delegated service accounts), `chat.app.*` and `chat.import`, `youtubepartner*`, and Classroom scopes.

`gmail.modify` blocks immediate permanent mail deletion, though Drive and editor scopes still allow destructive edits. Per-machine signing keys follow [commit signing](https://github.com/fmind/dot#commit-signing). OAuth capability never authorizes deletion or contacting others (including Cloud Support cases); GCP permissions stay in IAM. Editing config does not alter issued tokens: re-authenticate to add scopes and run `dot setup github` to strip excluded ones. `dot login github`, `dot setup github`, and `dot doctor --deep` warn when `gh` stored a plaintext token in `hosts.yml` (no keyring accepted it): unlock the macOS Keychain or Linux Secret Service keyring (or create a persistent `login` collection / `default` alias), then run `gh auth logout` and `dot setup github`.

## Colab ADC

ADC replaces its whole grant per login, so `auth.gcp.adc_scopes` holds every consumer's scope: `gcloud` defaults (`openid`, `userinfo.email`, `cloud-platform`, `sqlservice.login`), `colaboratory`, and read-only sensor scopes (`bigquery.readonly`, `logging.read`, `cloud-platform.read-only`). `dot login gcp` and `dot login colab` share that list; `dot login colab` refuses a list missing Colab scopes, re-authorizes only when scoped refresh fails (or with `--force`), and verifies session access (45s timeout each, no VM allocated):

```bash
gcloud auth application-default print-access-token --scopes=<auth.gcp.adc_scopes> >/dev/null  # readiness; never print the token
gcloud auth application-default login --scopes=<auth.gcp.adc_scopes>               # only when needed
colab --auth=adc sessions
```

Session access alone does not prove full scopes, and an empty listing passes only without auth-failure diagnostics (Colab can exit 0 on ADC failure). `--dry-run` prints commands without probing; unknown failures need native inspection. Colab updates shared ADC without changing the `gcloud` CLI account. Repair or unset `GOOGLE_APPLICATION_CREDENTIALS` before changing stored ADC, and rerun `dot login colab` if `gcloud auth login --update-adc` overwrites ADC scopes.

## Customer overrides and isolation

Nonempty `HF_TOKEN` overrides the HF token file; set `HF_TOKEN_PATH` before starting Python to pick another file (a missing file yields anonymous access, not an auth error on public resources). Kaggle's personal access-token file overrides legacy keys and OAuth (`KAGGLE_CONFIG_DIR` does **not** redirect it; Kaggle 2.2 falls back to legacy/OAuth if a token is invalid), so set `KAGGLE_API_TOKEN` explicitly for customer work. OpenCode's saved login can override env keys: set project `provider.openrouter.options.apiKey` to an env/file reference or isolate `XDG_DATA_HOME`. Empty env vars do not universally disable native credentials; for strict customer isolation, use a separate OS user, container, or dedicated `$HOME`. See [HF env vars](https://huggingface.co/docs/huggingface_hub/en/package_reference/environment_variables), [Kaggle token resolver](https://github.com/Kaggle/kaggle-sdk-python/blob/main/kagglesdk/kaggle_env.py), and [OpenCode providers](https://opencode.ai/v2/docs/providers/).

## Scoped credentials

`dot secret run NAME -- COMMAND ...` uses an existing `NAME` env value first, else `~/.config/dot/secrets/NAME`, failing before exec on empty values, missing/insecure files, or malformed credentials without retrying personal credentials on auth failure. Use ordinary commands for customer profiles and ADC; this opt-in helper passes `NAME` only to child processes (not a sandbox or env scrubber; nest calls for multiple keys). Shell startup exports no API keys, and native HF, Kaggle, and OpenCode logins seed only when absent; see [secret management](https://github.com/fmind/dot#secret-management).

Only `OPENROUTER_MANAGEMENT_KEY` (read-only usage reporting) is managed here. `SONARQUBE_CLI_KEYCHAIN_FILE` keeps `sonar` tokens in `~/.sonar/sonarqube-cli/tokens.json` (`0600`) without macOS Keychain prompts ([sonarqube](../../code-security/references/sonarqube.md)), and Vault (`vault kv get -field=<key>`) or Bitwarden (`bw get password`) secrets may be read only when piped directly into a consumer's stdin—never onto stdout, argv, or transcripts. Google model access uses ADC ([GCP Agent Platform](../../model-providers/references/gcp-agent-platform.md)); `ANTIGRAVITY_SDK_API_KEY`, `JULES_API_KEY`, `STITCH_ACCESS_TOKEN`, `UV_PUBLISH_TOKEN`, and `VERTEX_API_KEY` are retired (delete leftovers in `~/.config/dot/secrets/` and revoke at the provider). PyPI publishes via CI [Trusted Publishing](https://docs.pypi.org/trusted-publishers/), and `dot secret run` rejects `UV_PUBLISH_TOKEN`; use native `uv publish` with explicit credentials for other registries.
