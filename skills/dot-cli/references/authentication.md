---
name: authentication
description: "Inspect and apply configured provider login, OAuth scopes, and account policy."
---

# Workstation Authentication

Login checks current authentication and scopes before opening a browser. `--force` repeats authentication; `--dry-run` previews possible commands without executing probes. Unknown status fails with recovery guidance instead of starting authentication. Repair or remove environment-token overrides when they prevent OAuth updates.

Workspace project selection uses the setup argument, then `GWS_PROJECT`, then `auth.workspace.project`. GitHub host selection uses `--host`, then `GH_HOST`, then `auth.github.host`. Inspect policy with `dot config show` and edit it with `dot config edit`: `auth.github.scopes`, `auth.github.remove_scopes`, `auth.workspace.scopes`, `auth.workspace.apis`, and `auth.probe_timeout_seconds`. Maps merge with defaults; configured lists replace the entire default list.

The default policy covers repository, publishing, document, mail, calendar, contact, Chat, and Apps Script workflows, including Gmail settings/filter and Chat read-state management. It excludes GitHub repository/package deletion scopes and permits SSH key creation without key administration. Gmail uses `gmail.modify`, which excludes immediate permanent message deletion; full Drive and other editing scopes can still permit destructive operations. OAuth capability does not authorize deletion or contacting others. GCP permissions remain controlled by IAM. Applying configuration does not change issued tokens: authenticate again for new scopes and use `dot setup github` to remove excluded grants. Personal Google accounts need a Workspace policy without `directory.readonly`.

## Customer overrides and isolation

**Customer accounts:** Hugging Face's nonempty `HF_TOKEN` overrides its token file; set `HF_TOKEN_PATH` before starting Python when selecting a separate file. Kaggle's personal access-token file takes precedence over legacy keys and OAuth; `KAGGLE_CONFIG_DIR` does **not** redirect it. Select `KAGGLE_API_TOKEN` explicitly for customer work. OpenCode's saved login can override an environment key; use project `provider.openrouter.options.apiKey` with an environment/file reference, or isolate its login with `XDG_DATA_HOME`. Empty environment variables are not a universal way to disable native credentials. See the [HF environment reference](https://huggingface.co/docs/huggingface_hub/en/package_reference/environment_variables), [Kaggle token resolver](https://github.com/Kaggle/kaggle-sdk-python/blob/main/kagglesdk/kaggle_env.py), and [OpenCode providers](https://opencode.ai/docs/providers/).

Kaggle 2.2.4 tries legacy keys and OAuth if an access token is invalid; the scoped helper does not change native authentication behavior. For strict customer separation, use a separate OS account/container or a dedicated home and credential configuration without personal logins. A missing customer HF token file yields no saved token, but may permit anonymous operations; it does not guarantee an authentication error for public resources.

## Scoped credentials

`dot secret run NAME -- COMMAND ...` uses an existing `NAME` environment value first, then `~/.config/dot/secrets/NAME`. An explicitly empty value, missing/insecure file, or malformed credential fails before the command starts. It never retries with personal credentials after an authentication failure. This helper is an explicit opt-in to personal credentials: use the ordinary command for customer profiles and ADC. Child processes inherit the selected key and the rest of the existing environment; the parent shell does not gain the key. This is credential scoping, not a sandbox or an environment scrubber. Arguments, terminal input/output, and exit status are preserved. Nest the helper if a command needs multiple keys.

The managed scoped keys are `ANTIGRAVITY_SDK_API_KEY`, `VERTEX_API_KEY`, `JULES_API_KEY`, `STITCH_ACCESS_TOKEN`, and `OPENROUTER_MANAGEMENT_KEY` (read-only OpenRouter usage reporting). `VERTEX_API_KEY` replaces the personal AI Studio credential; SDKs must read it explicitly. Prefer ADC and never map it into globally auto-discovered Google key variables. See [GCP Agent Platform defaults and key fallback](../../model-providers/references/gcp-agent-platform.md). `UV_PUBLISH_TOKEN` is reserved for `dot secret publish`, which fixes the upload/check URLs to PyPI, disables project configuration and alternate authentication, and rejects conflicting publishing environment settings. An existing `UV_PUBLISH_TOKEN` wins. It accepts distribution paths/globs and `--dry-run`; use native `uv publish` for other options or registries. [uv publishing documentation](https://docs.astral.sh/uv/guides/package/).
