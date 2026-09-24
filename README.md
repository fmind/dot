# Dot

My personal dotfiles for **AI-driven, CLI-first** development on Linux and macOS: shell, editor, agent harnesses, skills, and a typed Python CLI, managed with [chezmoi](https://www.chezmoi.io/) (files) and [mise](https://mise.jdx.dev/) (tools & tasks). Built for my workstations; published for anyone who wants to read, borrow, or fork.

[![CI](https://github.com/fmind/dot/actions/workflows/ci.yml/badge.svg)](https://github.com/fmind/dot/actions/workflows/ci.yml) [![Release](https://img.shields.io/github/v/release/fmind/dot)](https://github.com/fmind/dot/releases/latest) [![License](https://img.shields.io/github/license/fmind/dot)](LICENSE)

> [!IMPORTANT]
> Personal, opinionated dotfiles. Review before running; provided **as-is** without warranty (see [LICENSE](LICENSE)).

| Platform                           | Tool lockfiles | CI                                |
| ---------------------------------- | -------------- | --------------------------------- |
| Linux x86-64 (glibc 2.39 or newer) | Yes            | Repository gate on `ubuntu-24.04` |
| macOS Apple Silicon                | Yes            | Template rendering only           |
| Anything else                      | No             | Not tested                        |

The CI gate renders the chezmoi templates as a dry run and runs the static checks, tests, and build; it does not execute `install.sh` end to end.

[Install](#installation) · [Use](#everyday-use) · [Tasks](#repository-tasks) · [Credentials](#credentials) · [Adapt](#adapting-this)

## Highlights

- **Shell & Terminal** — [Fish](https://fishshell.com/) with [Starship](https://starship.rs/), [Atuin](https://atuin.sh/), [zoxide](https://github.com/ajeetdsouza/zoxide), [fzf](https://github.com/junegunn/fzf), [Ghostty](https://ghostty.org/), and [Zellij](https://zellij.dev/).
- **Editor** — [Neovim](https://neovim.io/) powered by [LazyVim](https://www.lazyvim.org/).
- **AI Harnesses & Skills** — Shared persona (`AGENTS.md`) and [Agent Skills](https://agentskills.io) ([`skills/`](skills/)) for [Antigravity](https://antigravity.google/) (`agy`), [Claude Code](https://claude.com/claude-code), [OpenAI Codex](https://developers.openai.com/codex/) (`codex`), [OpenCode](https://opencode.ai/), [GitHub Copilot](https://github.com/features/copilot), and [Grok Build](https://x.ai/build) (`grok`).
- **Python & Cloud Stack** — Typed Python with uv, Ruff, ty, pytest, Django, Litestar, and Google ADK, plus OpenTofu for infrastructure.
- **`dot` CLI** — Typed Python tool for workspace automation, health checks, session archives, and diagnostics ([`dot/`](dot/)).
- **One Theme, Every Tool** — [fmind/theme](https://github.com/fmind/theme). Native theme files cover editors, shells and dashboards.

## Prerequisites

The installer requires mise 2026.9.10 or newer; it installs exactly that tested version when mise is absent but stops if an existing version is too old.

### Host Packages

The bootstrap installs user-space tools via mise, but requires host build tools, Git, curl, and native credential storage. Linux requires glibc 2.39 or newer (Debian 13 or Ubuntu 24.04 and newer) for the prebuilt Tree-sitter CLI:

```bash
# Linux (Debian/Ubuntu)
sudo apt install -y git curl libatomic1 build-essential gnome-keyring

# macOS
xcode-select --install
```

### GitHub Authentication

The managed Git configuration sends GitHub pushes over SSH, including repositories cloned over HTTPS. Generate an SSH key and register the public key in [GitHub Settings Keys](https://github.com/settings/keys) before pushing; the public clone below does not require authentication:

```bash
ssh-keygen -t ed25519 -a 100 -C "your_email@example.com"
```

### Recommended Tools (Optional)

- **Terminal**: [Ghostty](https://ghostty.org/docs/install/binary).
- **Containers**: A Docker-compatible container engine (Docker or Podman) if building container images.
- **Desktop notifications**: Codex, Claude, Grok, Antigravity, and Copilot notify when a prompt finishes. Linux needs a session D-Bus and a notification service; macOS uses its native service; headless sessions skip delivery. Restart open harnesses after their hook configuration changes. In Codex, review and trust new or changed hooks through `/hooks` before they can run. See [agent-harnesses](skills/agent-harnesses/SKILL.md) and [agy](skills/agy/SKILL.md) for Antigravity.

## Installation

> [!WARNING]
> Agent configurations default to autonomous execution with broad permissions. Use in trusted workspaces and review each harness's settings before use. Each apply runs `dot trust all`, so harnesses trust the `pull.directories` workspaces and their repositories whose GitHub `origin` owner is in `trust.github_owners`, without prompting (run `dot trust` in a new clone). Mise trust is separate and machine-local (see [Adapting this](#adapting-this)).

```bash
# Clone into the chezmoi source directory
git clone https://github.com/fmind/dot.git ~/.local/share/chezmoi

# Run the installer
bash ~/.local/share/chezmoi/install.sh
```

Open a new shell and run `dot doctor` to check your installation. Use `dot completion --check` to check Fish completions, or `dot completion` to regenerate them. Generation reports individual tool failures and continues without failing setup; `--check` returns a failure status if any generator fails. Failed generators leave existing scripts intact.

Set `SKIP_GIT_PULL=true` if bootstrapping from an existing local checkout without fetching upstream.

To finish an interrupted setup, rerun the installer. From an initialized checkout, `mise run full` reapplies files and synchronizes the locked tools, current `dot`, trust, theme cache, and completions. It also repairs an older `dot` that lacks `trust`; no manual trust command or second apply is needed.

### What the installer does

Read [`install.sh`](install.sh) first. It executes third-party code with your user's privileges:

1. When mise is absent, it downloads `https://mise.run` completely over HTTPS before running it with `bash`, then installs chezmoi through mise. An interrupted download fails without executing a partial script.
1. `chezmoi init` prompts for your identity (below). The locked repository tools install first, then `chezmoi apply --force --exclude scripts` writes files before the global tools install. Hooks wait until the locked global tools and current `dot` are installed; a complete `chezmoi apply --force` then sets folder trust and builds the bat theme cache.
1. Apply downloads the [Grok](run_once_after_install-grok.sh.tmpl) and [Antigravity](run_once_after_install-antigravity-cli.sh.tmpl) vendor installers over HTTPS and runs them with `bash` when those CLIs are missing; both CLIs then update themselves.
1. Apply fetches theme files from [fmind/theme](https://github.com/fmind/theme) `main` without a checksum ([`.chezmoiexternal.toml.tmpl`](.chezmoiexternal.toml.tmpl)); font archives are pinned by SHA-256.
1. mise installs every tool in [`dot_config/mise/config.toml.tmpl`](dot_config/mise/config.toml.tmpl) at the locked version. Signature and provenance verification (cosign, minisign, SLSA, GitHub attestations) is off on the workstation; the repository `mise.toml` keeps mise's defaults, so CI verifies the repository toolset. The workstation uses lockfile digests where the backend records them; `minimum_release_age = "0d"` makes new releases eligible immediately when resolving `latest`. Format 2 also locks supported npm and pipx dependency graphs in `dot_config/mise/locks/`; `mise run lock` captures those files with the global lockfile. First fetches are unverified; that file states the trade-off.

Setup installs Google Sans for text, Google Sans Code for code, and [Google Sans Code Nerd Font Mono](https://github.com/ryanoasis/nerd-fonts/tree/master/patched-fonts/GoogleSansCode) for terminals.

### First-run prompts

`chezmoi init` asks for a Git name, Git email, and GitHub username. The defaults in [`.chezmoi.toml.tmpl`](.chezmoi.toml.tmpl) are mine: enter your own. `install.sh` forwards extra arguments to `chezmoi init`, so answers can be supplied up front:

```bash
bash ~/.local/share/chezmoi/install.sh \
  --promptString "What is your Git name=Ada Lovelace" \
  --promptString "What is your Git email address=ada@example.com" \
  --promptString "What is your GitHub username=ada"
```

`--promptDefaults` accepts my identity without asking; use it only for dry runs. Answers are stored in `~/.config/chezmoi/chezmoi.toml`.

### Shell

Fish becomes the interactive shell through the terminal, not `chsh`: Ghostty sets `command` to the mise-installed Fish and Zellij sets `default_shell "fish"`. The login shell is unchanged; the managed blocks in `~/.bashrc` and `~/.profile` (and `~/.zprofile` on macOS) only add the mise paths and `mise activate`. In another terminal emulator, run `fish` or point its shell command at `~/.local/share/mise/shims/fish`.

### Dot configuration

The CLI optionally reads `~/.config/dot.yaml` and merges its values with the [built-in defaults](dot/src/fmind_dot/config.py). Select another file with `DOT_CONFIG_PATH` or `dot --config <path>`; the explicit flag takes precedence. A missing default file uses built-in defaults, while a missing explicitly selected file is an error.

`~/.config/dot.yaml` and `~/.config/dot.*.yaml` stay machine-local: both Git and chezmoi ignore their source equivalents. Alternate profiles are loaded only when explicitly selected.

Use `dot config show` to inspect effective settings, `dot config validate` to check them, and `dot config edit` to edit the file (through its source when chezmoi manages it). Command help and the [Dot CLI guide](skills/dot-cli/SKILL.md) describe available operations.

### Usage and subscription settings

Usage reports show tokens, coverage dates, and estimated API value in USD. Estimates are separate from actual costs and subscriptions. See the [usage guide](skills/agent-usage/SKILL.md) for reports and limitations.

Monthly reports use UTC. For subscription cycles, set the renewal day, timezone, and optional monthly charge in USD:

```yaml
# Docs: https://github.com/fmind/dot
agent:
  subscriptions:
    codex:
      renewal_day: 15
      timezone: Europe/Paris
      monthly_usd: 20
```

See the [billing reference](skills/agent-usage/references/queries.md#monthly-and-subscription-reports) for cycle boundaries and coverage limitations.

## Everyday use

```bash
dot --help                # Discover commands
dot doctor                # Check workstation health
dot config show           # Inspect effective settings
dot agent stats           # Review agent usage and prompt statistics
dot orphan                # List files chezmoi deployed but no longer manages
```

Edit managed files in `~/.local/share/chezmoi`, preview the changes, then apply them. See the [Dot CLI guide](skills/dot-cli/SKILL.md) for command details.

## Repository tasks

Run these from `~/.local/share/chezmoi`. Use `mise tasks` for the full list and aliases; [`mise.toml`](mise.toml) owns the definitions.

| Command                                         | Purpose                                                              |
| ----------------------------------------------- | -------------------------------------------------------------------- |
| `mise run diff`                                 | Preview pending dotfile changes                                      |
| `mise run apply`                                | Apply dotfiles and eligible hooks                                    |
| `mise run full` / `mise run mf`                 | Apply files, install locked tools and dot, run hooks and completions |
| `mise run deploy`                               | Build and install the local `dot` CLI                                |
| `mise run upgrade`                              | Upgrade dependencies, tools, and plugins; apply and reinstall        |
| `mise run check:docs` / `mise run check:skills` | Validate documentation and skill contracts                           |
| `mise run check`                                | Run static checks and security scans                                 |
| `mise run test`                                 | Run Python and repository tests                                      |
| `mise run all`                                  | Format, check, test, and build                                       |
| `mise run release -- --wait`                    | Commit, push, publish, and verify a release                          |

`all` rewrites formatting; it does not apply dotfiles. Pre-release qualification lives in the [verify guide](.agents/skills/dot-verify/SKILL.md), release prerequisites and recovery in the [release guide](.agents/skills/dot-release/SKILL.md); contributor rules live in [AGENTS.md](AGENTS.md).

## Agent skills

Skills use the standard `~/.agents/skills/` directory. Setup creates a real directory and links each package from this repository's [`skills/`](skills/) catalog into it. Other packages can be directories or individual links in the same location; names must be unique. Packages in this catalog may reference sibling skills, so check dependencies before copying one folder on its own. Restart agent sessions to refresh discovery.

Authoring: [skillify](skills/skillify/SKILL.md). Catalog maintenance and diagnostics: [skill maintenance guide](.agents/skills/dot-skills/SKILL.md).

### Upgrading the skill catalog

Upgrading from any v6.x release? Links to retired skills stay in `~/.agents/skills`; back up confirmed links as described in [retired links](.agents/skills/dot-skills/references/installed-links.md#retired-links), then restart your agents. Fresh installations need no cleanup.

## Credentials

### Secret Management

Secrets are no longer exported at shell startup. Native credential files work in Fish, Bash, Zsh, task runners, and Python SDKs; remaining keys are supplied explicitly to one command with `dot secret run`. Managed secret files are private (`0600`), with encrypted sources in Git; existing native files are preserved, including their permissions. This reduces inherited credentials; it does not isolate programs running as your user.

| Tool                       | Personal default                    | Customer override                                                                |
| -------------------------- | ----------------------------------- | -------------------------------------------------------------------------------- |
| Hugging Face CLI / Hub SDK | `~/.cache/huggingface/token`        | `HF_TOKEN`, or `HF_TOKEN_PATH` selecting a separate token file                   |
| Kaggle CLI / SDK           | `~/.kaggle/access_token`            | `KAGGLE_API_TOKEN` containing a token or an absolute token-file path             |
| OpenCode                   | `~/.local/share/opencode/auth.json` | Project provider configuration, or a separate `XDG_DATA_HOME` with its own login |
| PyPI publishing            | `dot secret publish`                | Use ordinary `uv publish` with the customer's credentials and registry           |

Native files are seeded only when absent (`create_` sources); Kaggle seeding is also skipped when a default legacy or OAuth credential file exists: later logins and account switches survive apply. Deleting a seeded file allows the next apply to recreate the personal default; to stop seeding it, add its target path to your chezmoi ignore rules or remove its source. Seeds use the default paths above; custom `HF_HOME`, `HF_TOKEN_PATH`, `XDG_CACHE_HOME`, or `XDG_DATA_HOME` need their own login. Use `hf auth login`, `kaggle auth login`, and OpenCode's `/connect` for native authentication.

Customer credentials must be selected explicitly; native tools have different precedence and fallback rules. See [customer overrides and isolation](skills/dot-cli/references/authentication.md#customer-overrides-and-isolation), including Kaggle legacy/OAuth behavior and OpenCode project configuration.

```bash
# Paths contain no secrets and work in Fish, Bash, and Zsh.
env HF_TOKEN_PATH="$HOME/.config/customer/hf-token" hf auth whoami
env KAGGLE_API_TOKEN="$HOME/.config/customer/kaggle-token" kaggle datasets list --mine

# Explicit personal credentials for one process tree, including a Python SDK or task.
dot secret run VERTEX_API_KEY -- uv run app.py # Explicit GCP Agent Platform key fallback; app reads this name.
dot secret run STITCH_ACCESS_TOKEN -- mise run design

# PyPI only; ordinary uv / uv run never load this token.
dot secret publish --dry-run
dot secret publish
```

`dot secret run` preserves an existing environment value; an empty value fails instead of selecting the personal key. It loads only the named credential and preserves child arguments, terminal I/O, and exit status. The scoped keys are `ANTIGRAVITY_SDK_API_KEY`, `VERTEX_API_KEY`, `JULES_API_KEY`, and `STITCH_ACCESS_TOKEN`. Use ordinary commands for customer profiles and ADC. Personal model integrations default to GCP Agent Platform with ADC, project `ai-studio-fmind`, location `global`, model `gemini-3.8-flash`, and high thinking; OpenCode keeps OpenRouter. The GCP Agent Platform key replaces the personal AI Studio key and is explicit-only or a last resort after reporting ADC failure. Never export it as `GEMINI_API_KEY` or `GOOGLE_API_KEY`. See [model defaults and billing](skills/model-providers/references/gcp-agent-platform.md) and [scoped credentials](skills/dot-cli/references/authentication.md#scoped-credentials).

**Upgrade:** apply the dotfiles and install the updated `dot` CLI together, then restart terminals, terminal multiplexers, editors, and agents from a clean login session. Existing processes retain their old environment; merely sourcing the new file or launching a child shell does not remove it. The retained `secrets.fish` is an inert migration stub. Remove any duplicate key exports from your local `~/.private.fish`; keep that file for non-secret machine settings.

Only the owner's age key decrypts the committed seeds. Without `~/.config/chezmoi/key.txt`, apply skips the encrypted credentials; a different key at that path fails decryption. **Back up this key.** For a fork, replace the recipient in [`.chezmoi.toml.tmpl`](.chezmoi.toml.tmpl) and remove/re-encrypt all credential sources. To add a scoped key, create `~/.config/dot/secrets/NAME` privately using an editor or secret manager, set its mode to `0600`, then `chezmoi add --encrypt` that file; never put the value in command arguments. Set native credential files to `0600` before capturing them with `chezmoi add --encrypt --create <path>`; seeded files are not overwritten by subsequent source changes, so rotate the active native credential through its tool and refresh the encrypted seed separately.

### Authentication & Logins

`dot login` owns GitHub, Google Workspace, and Google Cloud; it drives `gh`, `gws`, and `gcloud`, which retain account/profile selection and credential storage:

| Provider                  | Command               |
| ------------------------- | --------------------- |
| GitHub                    | `dot login github`    |
| Google Workspace          | `dot login workspace` |
| Google Cloud and ADC      | `dot login gcp`       |
| Workspace, then GCP + ADC | `dot login google`    |

`dot login` alone lists providers. `dot login google` stops on failure and excludes GitHub. Use `dot setup github` to reconcile GitHub scopes and remove configured excluded grants, and `dot setup workspace <project-id>` to enable missing Workspace APIs and configure its OAuth client.

Configure authentication under `auth` in the [Dot configuration](#dot-configuration); only non-default keys are needed:

```yaml
# Docs: https://github.com/fmind/dot
auth:
  workspace:
    project: my-workspace-project
```

OAuth scopes grant capability, not authority to delete data or contact others; see the [authentication guide](skills/dot-cli/references/authentication.md) for selection precedence, scope policy, re-authentication after scope changes, and authentication checks.

Agent harnesses authenticate themselves:

| Harness                | Command                                      | Auth Type             |
| ---------------------- | -------------------------------------------- | --------------------- |
| **Antigravity CLI**    | `agy`                                        | On-demand prompt      |
| **Claude Code**        | `claude auth login` (or `claude` → `/login`) | Interactive / browser |
| **GitHub Copilot CLI** | `copilot login` (or `copilot` → `/login`)    | Interactive / browser |
| **Grok Build CLI**     | `grok login` (or `XAI_API_KEY`)              | Interactive / API key |
| **OpenAI Codex CLI**   | `codex login`                                | Interactive           |
| **OpenCode CLI**       | `opencode` → `/connect`                      | OpenRouter API key    |

Claude's managed settings remove `CLAUDE_CODE_USE_VERTEX`, `ANTHROPIC_VERTEX_PROJECT_ID`, `CLOUD_ML_REGION`, `ANTHROPIC_DEFAULT_SONNET_MODEL`, and `ANTHROPIC_DEFAULT_HAIKU_MODEL` from the settings `env` object on each apply. Keep these provider overrides in the environment of the process that launches Claude; unrelated host environment settings are preserved.

No workspace MCP server is preconfigured; add one with [mcp-setup](skills/mcp-setup/SKILL.md) and pass its token to one command with `dot secret run`.

## Adapting this

Fork rather than install as-is. Owner-specific values to replace:

1. **Identity prompts**: the defaults in [`.chezmoi.toml.tmpl`](.chezmoi.toml.tmpl), and the clone URL in [`install.sh`](install.sh).
1. **Local Git profiles**: `~/.gitconfig` includes `~/.config/git/config.local` last when present, so its scalar settings override the managed defaults. Put `includeIf` rules there to select repository-specific profiles. That file and sibling `config.*` files stay outside Git and chezmoi management.
1. **Secrets**: the age `recipient` in `.chezmoi.toml.tmpl` and all encrypted credential sources; replace or remove them and configure your own native logins and scoped keys as described in [Secret Management](#secret-management).
1. **Persona**: [`dot_agents/AGENTS.md`](dot_agents/AGENTS.md) deploys to `~/.agents/AGENTS.md`, names me, and encodes my working rules; every harness loads it.
1. **Workspace directories**: `~/fmind`, `~/fmind-ai`, and `~/mlops-courses` are Claude `additionalDirectories` in [`dot_claude/modify_settings.json`](dot_claude/modify_settings.json) and the `pull.directories` default of the `dot` CLI, which `dot trust all` uses for every harness (override in `~/.config/dot.yaml`). Mise trust is separate and machine-local: run `mise trust /path/to/mise.toml` for individual configs, or set `[settings].trusted_config_paths` in unmanaged `~/.config/mise/conf.d/trust.toml` to trust selected directory trees. Chezmoi does not overwrite that file.
1. **Theme**: files track [fmind/theme](https://github.com/fmind/theme) `main`; point [`.chezmoiexternal.toml.tmpl`](.chezmoiexternal.toml.tmpl) at your own or pin a commit.

## Uninstall / rollback

There is no uninstaller, and chezmoi keeps no backup of the files that `apply --force` replaced: back up your own dotfiles before installing. To remove the setup:

```bash
# List what chezmoi manages, before removing its state
chezmoi managed

# Remove chezmoi's source directory, configuration, and state; deployed files stay
chezmoi purge

# Remove mise and every tool it installed (--config also removes ~/.config/mise)
mise implode --config
```

Left behind, to delete by hand: the deployed files listed by `chezmoi managed`, the `# chezmoi: mise-*` blocks in `~/.bashrc`, `~/.profile`, and `~/.zprofile`, the `dot` CLI under `~/.local/share/fmind-dot` with its `~/.local/bin/dot` link, the Grok installation (`~/.grok` with its `~/.local/bin/grok` and `~/.local/bin/agent` links) and Antigravity (`~/.local/bin/agy`) installations, installed fonts, `~/.agents`, your age key, and any data the tools wrote. To roll back an update, check out the previous release tag in `~/.local/share/chezmoi` and run `chezmoi apply --force`; files added since then stay in place.

## Security

See [SECURITY.md](.github/SECURITY.md) to report a vulnerability.

## License

[MIT](LICENSE) © Médéric Hurier (Fmind)
