# Dot

My personal dotfiles for **AI-driven, CLI-first** development on Linux and macOS. Declarative, reproducible, and fast.

Managed with [chezmoi](https://www.chezmoi.io/) (files) and [mise](https://mise.jdx.dev/) (tools & tasks).

> [!IMPORTANT]
> Personal, opinionated dotfiles. Review before running; provided **as-is** without warranty (see [LICENSE](LICENSE)).

## Highlights

- **Shell & Terminal** — [Fish](https://fishshell.com/) with [Starship](https://starship.rs/), [Atuin](https://atuin.sh/), [zoxide](https://github.com/ajeetdsouza/zoxide), [fzf](https://github.com/junegunn/fzf), [Ghostty](https://ghostty.org/), and [Zellij](https://zellij.dev/).
- **Editor** — [Neovim](https://neovim.io/) powered by [LazyVim](https://www.lazyvim.org/).
- **AI Harnesses & Skills** — Shared persona (`AGENTS.md`) and [Agent Skills](https://agentskills.io) ([`skills/`](skills/)) for [Antigravity](https://antigravity.google/) (`agy`), [Claude Code](https://claude.com/claude-code), [OpenAI Codex](https://developers.openai.com/codex/) (`codex`), [OpenCode](https://opencode.ai/), [GitHub Copilot](https://github.com/features/copilot), and [Grok Build](https://x.ai/build) (`grok`).
- **Python & Cloud Stack** — Typed Python with uv, Ruff, ty, pytest, Django, Litestar, and Google ADK, plus OpenTofu for infrastructure.
- **`dot` CLI** — Typed Python tool for workspace automation, health checks, session archives, and diagnostics ([`dot/`](dot/)).
- **One Theme, Every Tool** — [fmind/theme](https://github.com/fmind/theme) uses dark syntax on white, with purple types, teal information, light-grey panels and bright active controls. Native theme files cover editors, shells and dashboards; bat and delta share the same syntax theme.
- **User-Space Toolchain** — CLIs managed declaratively in user space via [mise](https://mise.jdx.dev/) and dotfiles synced via [chezmoi](https://www.chezmoi.io/).

## Prerequisites

Tool lockfiles target Linux x86-64 and macOS Apple Silicon. The installer requires mise 2026.9.1 or newer; it installs mise when absent but stops if an existing version is too old.

Terminal recording with VHS additionally requires FFmpeg, ttyd, and the selected font. The managed toolchain supplies ttyd on Linux. On macOS, qualify a user-space ttyd build or a reviewed recording container; upstream currently publishes no macOS ttyd binary.

### Host Packages

The bootstrap installs user-space tools via mise, but requires host build tools, Git, curl, and native credential storage. Linux requires glibc 2.39 or newer (Debian 13 or Ubuntu 24.04 and newer) for the prebuilt Tree-sitter CLI:

```bash
# Linux (Debian/Ubuntu)
sudo apt install -y git curl libatomic1 build-essential gnome-keyring

# macOS
xcode-select --install
```

### ChromeOS / Crostini: Ghostty dead keys

On ChromeOS with a Debian Crostini container, US International dead keys can disappear in Ghostty when `GTK_IM_MODULE=cros` is set but the `cros-im` package is missing. Pasted or programmatically printed apostrophes, backticks, and tildes still display correctly, and typing works in the ChromeOS Terminal app. Check the package with `apt-cache policy cros-im`; if it reports `Installed: (none)`, install the host input-method integration manually:

```bash
sudo apt install cros-im
```

Close all Ghostty windows and reopen it normally, keeping US International selected. Verify that apostrophe followed by Space produces an apostrophe and apostrophe followed by `e` produces `é`. This repair was confirmed on Debian 13 Crostini; it does not apply to macOS, including Apple Silicon, or ordinary Linux installations. See the [ChromeOS input-method documentation](https://chromium.googlesource.com/chromiumos/platform2/+/HEAD/vm_tools/cros_im/).

### GitHub Authentication

The managed Git configuration sends GitHub pushes over SSH, including repositories cloned over HTTPS. Generate an SSH key and register the public key in [GitHub Settings Keys](https://github.com/settings/keys) before pushing; the public clone below does not require authentication:

```bash
ssh-keygen -t ed25519 -a 100 -C "your_email@example.com"
```

### Recommended Tools (Optional)

- **Terminal**: [Ghostty](https://ghostty.org/docs/install/binary). Setup installs [Google Sans Code Nerd Font Mono](https://github.com/ryanoasis/nerd-fonts/tree/master/patched-fonts/GoogleSansCode) and selects it in Ghostty.
- **Containers**: A Docker-compatible container engine (Docker or Podman) if building container images.

## Installation

> [!WARNING]
> Agent configurations default to autonomous execution with broad permissions. Use in trusted workspaces and review each harness's settings before use.

```bash
# Clone into the chezmoi source directory
git clone https://github.com/fmind/dot.git ~/.local/share/chezmoi

# Run the installer
bash ~/.local/share/chezmoi/install.sh
```

Set `SKIP_GIT_PULL=true` if bootstrapping from an existing local checkout without fetching upstream.

Google Sans is the default for application text and Google Sans Code for code; terminal apps inherit GoogleSansCode Nerd Font Mono from Ghostty. The managed installer supplies all three families from checksum-pinned official releases. Projects that embed fonts must still bundle their fonts.

Google Sans v14.000 and Google Sans Code v7.001 are installed per user under `GoogleSans` and `GoogleSansCodeOfficial` in the platform font directory, with their OFL licenses.

The terminal font is installed per user in `~/.local/share/fonts/GoogleSansCode` on Linux and `~/Library/Fonts/GoogleSansCode` on macOS, from the checksum-pinned Nerd Fonts v3.5.1 archive. After switching an existing installation, reopen Ghostty; on Linux, run `fc-cache -f ~/.local/share/fonts/GoogleSansCode` if the font is not detected yet.

The installer prompts for Git identity, applies the dotfiles and eligible installation hooks, installs the locked tools and `dot` CLI, and configures Git hooks and Neovim plugins. Open a new shell afterward, or use `~/.local/bin/dot --help` to check the installed CLI directly.

Standalone theme files follow `fmind/theme` on `main`, with no host-specific theme settings or release pin. The installer refreshes externals when applying dotfiles. For a direct chezmoi update, use `chezmoi apply --force --refresh-externals`; without the refresh flag, theme downloads can stay cached for 24 hours. Applications pick up the new theme on reload or restart.

### Theme coverage

chezmoi downloads standalone themes from upstream `main`. Tools that require merged configuration retain copied style blocks with upstream source comments; these snapshots update with this dotfiles repository, not automatically with upstream.

| Integration                                               | Theme delivery and selection                                                                                                                         |
| --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Ghostty, Zellij, Neovim, lualine, OpenCode                | External native files; fixed `fmind` selection (lualine follows Neovim).                                                                             |
| Fish, fzf, k9s, delta, ptpython                           | External native files; loaded through Fish startup, `FZF_DEFAULT_OPTS_FILE`, `K9S_SKIN`, Git include, and the ptpython config module.                |
| Atuin, bat, lsd, Yazi                                     | External native files; selected in native config. bat's apply hook rebuilds the syntax cache used by bat and delta; Yazi reads the same syntax file. |
| Starship, gh-dash, bottom, Lazydocker, LazyGit, Fastfetch | Copied palette or style blocks merged with managed behavior.                                                                                         |
| Antigravity, Claude Code, Grok, mise                      | Terminal colors or closest built-in light palette: `terminal`, `light-ansi`, `grokday`, and `base16`, respectively.                                  |

A terminal palette controls ANSI colors, not every hard-coded app color. Tools without a native fmind integration keep their supported UI settings. When upstream changes its palette, synchronize the copied style blocks to keep them consistent with the refreshed externals.

### Fish completions

Run `dot completion` after installing or updating tools to refresh Fish completions, including Dot and FKF, and the shell integration caches. Open a new Fish shell afterward. The selection and generators are configurable under `completions` in `dot config show`; unavailable tools are skipped.

### Python environment

Run `uv sync --locked` in each existing Python project to create its `.venv` before opening it in Neovim. LazyVim uses ty for types and navigation, Ruff for linting, formatting, and import sorting, and the project environment for pytest and debugging. mise supplies ty and Ruff ahead of Mason's tools. Python debugging uses uv to provide debugpy on demand; the first run may download it.

For a Python REPL with the project's dependencies, run `uv run --with ptpython ptpython` from that project. The globally installed `ptpython` has its own isolated environment.

The managed `~/.config/ruff/ruff.toml` provides a fallback for scratch scripts; a project's own Ruff configuration takes precedence. Copilot CLI uses the same mise-installed `ty` language server for Python navigation; `/lsp` shows its registration.

### Application preferences

Copilot and Antigravity settings merge with existing host state. Model and UI defaults seed missing values; subsequent native choices, account settings, and Antigravity workspace trust survive apply. Dot continues to manage execution policy, Vim mode, and notifications. Copilot updates through mise, with its native automatic updater disabled. Explicit `ANTIGRAVITY_CLOUD_PROJECT` and `ANTIGRAVITY_CLOUD_LOCATION` values override the saved cloud selection; without a project override, the saved selection is preserved.

Kubernetes tooling is project-scoped. On existing machines, retire the former global `~/.config/k9s/config.yaml`, `~/.config/stern/config.yaml`, and `~/.kube/kuberc` after preserving any needed preferences. Leave `~/.kube/config` and its cluster credentials and contexts intact.

Agent desktop notifications require a desktop notification service. Headless Linux sessions skip notifications; when a session bus exists without that service, the hook reports the skip without failing the agent turn. Other delivery failures remain errors.

### Dot configuration

The CLI optionally reads `~/.config/dot.yaml` and merges its values with the [built-in defaults](dot/src/fmind_dot/config.py). Select another file with `DOT_CONFIG_PATH` or `dot --config <path>`; the explicit flag takes precedence. A missing default file uses built-in defaults, while a missing explicitly selected file is an error.

Use `dot config show` to inspect effective settings, `dot config validate` to check them, and `dot config edit` to edit the file (through its source when chezmoi manages it). Command help and the [Dot CLI guide](skills/dot-cli/SKILL.md) describe available operations.

### Usage and subscription settings

Agent usage reports show recorded tokens, coverage dates, and an offline API-equivalent value in USD. The value uses standard model rates and is separate from provider-reported costs and subscription charges. It does not measure answer quality or money actually saved. See the [usage guide](skills/agent-usage/SKILL.md) for totals, monthly reports, source coverage, and refresh instructions.

Calendar months use UTC. To align reports with a subscription, add its renewal day and billing timezone to the optional Dot configuration. `monthly_usd` is optional and must be your comparable USD monthly charge; Dot does not fetch invoices or convert currencies. The example is illustrative, not an inferred subscription:

```yaml
# Docs: https://github.com/fmind/dot
agent:
  subscriptions:
    codex:
      renewal_day: 15
      timezone: Europe/Paris
      monthly_usd: 20
```

Configure each subscribed harness independently. Renewal days 29–31 use the month's last day when necessary. Cycles start at local midnight and end exclusively at the next renewal; daylight-saving changes follow the configured IANA timezone. Missing subscription settings remain unknown. Partial archives and incomplete pricing cannot establish a complete subscription comparison.

## Agent skills

Skills use the standard `~/.agents/skills/` directory. Dotfiles setup creates a real directory and links each package from this repository's [`skills/`](skills/) catalog into it. Other packages can be directories or individual links in the same location; names must be unique. Packages in this catalog may reference sibling skills, so check dependencies before copying one folder on its own.

If installed separately, Cursor's local CLI and editor discover the shared catalog; remote workers need their own project or worker skill installation. The catalog's FKF retrieval package is a reviewed snapshot of the author's newer FKF workflow: select the knowledge base's matching runtime before using it. Base locations and private instructions remain local to each base; installing the skill does not upgrade FKF or migrate knowledge.

To add a skill, create `~/skill-library/meeting-prep/SKILL.md` with a matching name, a description, and actionable instructions:

```markdown
---
name: meeting-prep
description: Prepare a meeting agenda from supplied notes. Use when planning a meeting.
---

# Prepare a Meeting

1. Identify the meeting objective and decisions needed from the supplied notes.
1. Draft a timed agenda and list missing information without inventing it.
```

Then install the package using an absolute, stable source path:

```bash
mkdir -p ~/.agents/skills
ln -s ~/skill-library/meeting-prep ~/.agents/skills/
```

Run this setup on each computer. An existing name makes `ln` fail without replacing it; inspect the existing package before choosing another name. Restart the agent session to refresh discovery. `dot agent doctor --agent codex --explain` checks package links and entrypoints as part of integration health; actual selection still needs a request that exercises the skill. For changes to this repository's catalog, follow the [skill maintenance guide](.agents/skills/dot-skills/SKILL.md), including link retirement and source relocation.

## Credentials

### Secret Management

API keys and credentials are split between two Fish configuration files:

1. **`~/.config/fish/conf.d/secrets.fish`** (shared, encrypted in repo): Decrypted automatically from `encrypted_private_secrets.fish.age`. Exports keys including `ANTIGRAVITY_SDK_API_KEY`, `GEMINI_API_KEY`, `HUGGINGFACE_API_TOKEN`, `JULES_API_KEY`, `KAGGLE_API_TOKEN`, `STITCH_ACCESS_TOKEN`, `STUDIO_API_KEY`, and `UV_PUBLISH_TOKEN`.

   To decrypt on apply, provision your private age key:

   ```bash
   mkdir -p ~/.config/chezmoi
   # Place your private key in key.txt and secure permissions
   chmod 600 ~/.config/chezmoi/key.txt
   ```

   > [!NOTE]
   > If `key.txt` is missing, `secrets.fish` is skipped during `chezmoi apply` via `.chezmoiignore`, allowing unprivileged bootstrap without personal secrets.

   > [!WARNING]
   > **Back up `~/.config/chezmoi/key.txt`.** It is not managed by chezmoi. If lost, encrypted repo files are unrecoverable.

1. **`~/.private.fish`** (local, untracked): Sourced automatically by `config.fish` for machine or project overrides:

   ```fish
   set -gx ANTIGRAVITY_CLOUD_PROJECT   "my-vertex-project"
   set -gx ANTIGRAVITY_CLOUD_LOCATION  "global"
   set -gx OPENCODE_GCP_PROJECT        "my-vertex-project"
   set -gx VERTEX_LOCATION             "global"
   set -gx GWS_PROJECT                 "my-workspace-project"
   ```

### Authentication & Logins

Use `dot login` to see providers, `dot login workspace` for Workspace, and `dot login all` for Workspace followed by Google Cloud and ADC. The sequence stops on failure and excludes GitHub. Use `dot login github` separately; `dot setup github` also removes configured excluded OAuth grants. Login checks current authentication and scopes before opening a browser; `--force` explicitly repeats authentication, and `--dry-run` previews possible commands without executing probes. Unknown status fails with recovery guidance instead of silently starting authentication.

Use `dot setup workspace <project-id>` to enable missing Workspace APIs and configure its OAuth client. The project comes from the argument, then `GWS_PROJECT`, then `auth.workspace.project`. GitHub host selection uses `--host`, then `GH_HOST`, then `auth.github.host`. Native tools retain account/profile selection and credential storage; environment-token overrides must be repaired or removed when they prevent OAuth updates.

Policy is exposed by `dot config show` and configurable through `dot config edit`: `auth.github.scopes`, `auth.github.remove_scopes`, `auth.workspace.scopes`, `auth.workspace.apis`, and `auth.probe_timeout_seconds`. Maps merge with defaults; a configured list replaces the entire default list. Existing schema-version-3 configuration remains valid. The configuration file is selected by `--config`, then `DOT_CONFIG_PATH`, then `~/.config/dot.yaml`.

```yaml
# Docs: https://github.com/fmind/dot
schema_version: 3
auth:
  github:
    host: github.com
  workspace:
    project: my-workspace-project
  probe_timeout_seconds: 45
cache:
  providers: [docker, hf, uv]
prune:
  providers: [dprint, hf, mise, npm, trivy, uv]
```

The former managed `login.toml`, `setup.toml`, `cache.toml`, and `prune.toml` files have been retired from `~/.config/mise/conf.d/`; other files there remain independently managed. Install the updated Dot CLI with the normal tool setup before using its new commands.

| Tool / Service           | Command                                           | Auth Type             |
| ------------------------ | ------------------------------------------------- | --------------------- |
| **GitHub CLI**           | `gh auth login`                                   | Browser OAuth         |
| **Google Cloud SDK**     | `gcloud auth login --update-adc`                  | ADC + OAuth           |
| **Google Workspace CLI** | `gws auth login`                                  | Browser OAuth         |
| **Antigravity CLI**      | `agy`                                             | On-demand prompt      |
| **Claude Code**          | `claude auth login` (or `claude` → `/login`)      | Interactive / browser |
| **OpenAI Codex CLI**     | `codex login`                                     | Interactive           |
| **OpenCode CLI**         | `gcloud auth login --update-adc`, then `opencode` | Vertex AI ADC         |
| **GitHub Copilot CLI**   | `copilot login` (or `copilot` → `/login`)         | Interactive / browser |
| **Grok Build CLI**       | `grok login` (or `XAI_API_KEY`)                   | Interactive / API key |

Use `dot setup github` to reconcile GitHub scopes and `dot setup workspace <project-id>` for Workspace setup. Select the account, project, APIs, and scopes deliberately through each provider's native CLI.

The configured policy retains repository, publishing, document, mail, calendar, contact, Chat, and Apps Script workflows. It adds Gmail settings/filter management and Chat read-state management, excludes GitHub repository/package deletion scopes, and permits SSH key creation without key administration. Gmail uses `gmail.modify`, which excludes immediate permanent message deletion; full Drive and other editing scopes can still allow destructive operations. OAuth capability does not authorize an agent to delete data or contact others. GCP resource permissions remain controlled by IAM. Applying configuration alone does not change issued tokens: authenticate again for new scopes, and use the explicit GitHub setup command to remove the listed old grants. Workspace directory lookup requires a Workspace account; personal Google accounts need a policy without `directory.readonly`.

Define PATs or session tokens for workspace MCP integrations on demand: `AIRTABLE_PAT`, `GITHUB_PERSONAL_ACCESS_TOKEN`, `DATABRICKS_HOST` / `DATABRICKS_TOKEN`, and `JIRA_URL` / `JIRA_USERNAME` / `JIRA_API_TOKEN`.

## License

[MIT](LICENSE) © Médéric Hurier (Fmind)
