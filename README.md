# Dot

My personal dotfiles for **AI-driven, CLI-first development** on Linux and macOS. [Chezmoi](https://www.chezmoi.io/) manages the files; [mise](https://mise.jdx.dev/) manages tools and tasks. Read, borrow, or fork to build your own workstation.

[![CI](https://github.com/fmind/dot/actions/workflows/ci.yml/badge.svg)](https://github.com/fmind/dot/actions/workflows/ci.yml) [![Release](https://img.shields.io/github/v/release/fmind/dot)](https://github.com/fmind/dot/releases/latest) [![License](https://img.shields.io/github/license/fmind/dot)](LICENSE)

[Install](#installation) · [Use](#everyday-use) · [Agents](#agent-layer) · [Credentials](#credentials) · [Adapt](#adapting-this)

<a href=".github/assets/dot-overview.svg">
  <img
    src=".github/assets/dot-overview.svg"
    alt="How dot works: clone this repository of dotfiles, persona, skills, tool baseline and encrypted credentials; install.sh bootstraps mise and chezmoi; chezmoi applies files, mise installs locked tools and the dot CLI checks health, so your Linux or macOS workstation gets its terminal, editor, Python, cloud tools and four agent harnesses. Change the source, never the deployed copy."
    width="960"
  >
</a>

## Highlights

- **Terminal:** Ghostty, Zellij, and Fish with Starship, Atuin, zoxide, fzf, yazi, and lazygit — tuned for fast keyboard navigation and ultrawide displays.
- **Editor:** Neovim with LazyVim, styled across every tool with [fmind/theme](https://github.com/fmind/theme).
- **Agents:** Antigravity (primary), Claude Code, Copilot, and OpenCode share one persona and [skill catalog](skills/); `dot agent session sync` archives local sessions and `dot agent stats` reports usage and costs (including retired Codex and Grok archives).
- **Development:** Python 3.14 with uv, Ruff, ty, and pytest, plus cloud and service CLIs; projects pin their own stack tools.
- **Automation:** the `dot` CLI checks workstation health, manages multi-repo workspaces, handles provider logins and scoped secrets, and tracks agent context budgets.

## Prerequisites

| Platform            | Requirements                            | CI coverage                            |
| ------------------- | --------------------------------------- | -------------------------------------- |
| Linux x86-64        | glibc 2.39+ (Debian 13 / Ubuntu 24.04+) | Full repository gate and starter tests |
| macOS Apple Silicon | macOS 15+, Xcode Command Line Tools     | Templates, Python, and starter tests   |

The macOS baseline follows [Homebrew's supported versions](https://docs.brew.sh/Installation#macos-requirements); other platforms are untested. CI validates templates, code, and builds without running the host installer end to end.

Install the host prerequisites first; everything else installs in user space:

```bash
# Debian / Ubuntu
sudo apt install -y git curl libatomic1 build-essential gnome-keyring xclip wl-clipboard libnotify-bin pulseaudio-utils
# ChromeOS Linux with GPU acceleration: allow Ghostty to open the GPU, then restart Linux
sudo usermod -aG render "$USER"

# macOS
xcode-select --install
```

The installer requires mise 2026.10.18 or newer and installs it if absent. [Ghostty](https://ghostty.org/docs/install/binary) is the recommended terminal. A container engine is optional: on macOS, mise installs Colima with the Docker CLI, Compose, and Buildx (`colima start` runs the engine); on Linux, install Docker Engine from your distribution.

## Installation

> [!WARNING]
> These are personal dotfiles: [adapt them](#adapting-this) and back up your files first. Setup overwrites managed files without backups. Agents run with broad autonomous permissions, and apply automatically trusts configured workspaces and owner-allowlisted repositories. Review the settings and [trust behavior](skills/dot-cli/references/daily-workflows.md#folder-trust) before use.

Inspect [`install.sh`](install.sh), then run:

```bash
git clone https://github.com/fmind/dot.git ~/.local/share/chezmoi
bash ~/.local/share/chezmoi/install.sh
```

Enter **your own** Git name, email, personal-repository email, and GitHub username when prompted (the defaults are mine). Open a new shell and run `dot doctor` to verify the workstation.

Rerun `install.sh` to resume an interrupted setup (`SKIP_GIT_PULL=true` skips fetching upstream). From an initialized checkout, `mise run full` reapplies files and synchronizes locked tools, `dot`, and completions.

### Shell

Ghostty and Zellij launch Fish while leaving your login shell untouched. Fish attaches to Zellij once at startup and returns to a plain shell when you detach or exit. In other terminals, run `fish` or set the shell command to `~/.local/share/mise/shims/fish`.

## Everyday use

```bash
dot --help                # Discover commands
dot doctor                # Check workstation health
dot doctor --headroom     # One-line disk and memory check before large work
dot config show           # Inspect effective settings
dot agent stats           # Review agent usage and prompt statistics
dot status --fetch        # Refresh remotes, then show repository status
dot orphan                # List files no longer managed by chezmoi
```

Edit managed files in `~/.local/share/chezmoi`, then preview and apply:

```bash
cd ~/.local/share/chezmoi
mise run diff
mise run apply
```

The [Dot CLI guide](skills/dot-cli/SKILL.md) covers every command, diagnostic, and recovery workflow.

Daily keyboard and shell ergonomics:

- **Fish abbreviations:** `a` runs `agy` (`ac` continue, `ai` interactive prompt, `ap` print), `g` git (`gl` lazygit), `m` mise (`mr` `mise run`), `v` Neovim, `y` yazi, and `h` `dot` (`hd` doctor, `hh` headroom, `hs` repos needing attention with fetch, `hp` pull, `ho` orphans, `hc` caches, `ha` agent stats).
- **Zellij:** `Alt a` opens Antigravity, `Alt g` lazygit, `Alt y` yazi, and `Alt /` the session manager. New panes (`Alt n`) tile as up to four equal columns for 21:9 or 32:9 ultrawide displays; a fifth pane (or `Ctrl b`, `Space`) switches to a half-stacked layout. Multi-pane and active-program sessions stay resurrectable from `Alt /` after a reboot or kill; detach (`Ctrl o`, `d`) to park a single-pane shell until the next reboot.
- **Neovim:** `<leader>gm` toggles a buffer's Git diff between the index and the default branch's merge-base. `Tab` accepts completions, `Enter` inserts a newline (and continues or outdents lists in Markdown, text, and commit buffers), and `mise lsp` powers diagnostics and completions in `mise.toml`.

### Dot configuration

Machine-local settings live in unmanaged `~/.config/dot.yaml` and merge with [built-in defaults](dot/src/fmind_dot/config.py). Edit and validate them with `dot config edit`, or select an alternate `~/.config/dot.*.yaml` profile via `dot --config <path>` or `DOT_CONFIG_PATH`.

### Usage reports

`dot agent stats` separates token counts and estimated API value from billed costs (`--monthly` groups by UTC calendar month). `dot agent session sync` captures longer local transcripts before harnesses prune them; see the [usage guide](skills/agent-usage/SKILL.md).

## Repository tasks

Run these from the checkout; `mise tasks` lists every task and alias.

| Command            | Purpose                                                                         |
| ------------------ | ------------------------------------------------------------------------------- |
| `mise run diff`    | Preview dotfile changes                                                         |
| `mise run apply`   | Apply files and eligible hooks                                                  |
| `mise run doctor`  | Check workstation health (`dot`, chezmoi, and mise)                             |
| `mise run full`    | Install locked repo and global tools, apply dotfiles, deploy `dot`, completions |
| `mise run upgrade` | Upgrade dependencies, tools, the theme pin, and plugins (includes `full`)       |
| `mise run all`     | Check, test, and build the repository (without rewriting files or deploying)    |

Contributor details: [AGENTS.md](AGENTS.md), [verification](.agents/skills/dot-verify/SKILL.md), and [releases](.agents/skills/dot-release/SKILL.md). Python follows the latest 3.14 patch release until required tools ship 3.15 wheels.

## Agent layer

<a href=".github/assets/agent-layer.svg">
  <img
    src=".github/assets/agent-layer.svg"
    alt="One agent layer for four harnesses: the persona, skill catalog and per-host settings are written once in this repository, deployed by chezmoi to Antigravity, Claude Code, GitHub Copilot and OpenCode; dot agent session sync archives their sessions and dot agent stats reports usage."
    width="960"
  >
</a>

Antigravity, Claude Code, Copilot, and OpenCode share one persona ([`dot_agents/AGENTS.md`](dot_agents/AGENTS.md)) and one skill catalog ([`skills/`](skills/)). Launching `agy` from Fish or Zellij (`Alt a`) puts mise shims first on `PATH` so agent commands respect each project's tool pins. General-purpose subagents inherit the same persona and skills without custom role definitions; see [cross-harness agents](skills/agent-project/references/cross-harness-agents.md).

## Agent skills

Setup links [`skills/`](skills/) into `~/.agents/skills/` alongside independently installed packages (restart agent sessions after catalog changes). See [skill authoring](skills/skillify/SKILL.md), [catalog maintenance](.agents/skills/dot-skills/SKILL.md), and [retired-link cleanup](.agents/skills/dot-skills/references/installed-links.md#retired-links).

Everyday slash commands:

- **Deliverables & writing:** `/clipboard` copies the last deliverable (or `/clipboard <selection>`) via native OS tools ([clipboard](skills/clipboard/SKILL.md)); `/stakeholder-writing` turns technical work into decision-ready reports and proposals; `/draft-doc` creates Google Docs (`.md` or `.gdoc`); `/draft-mail` drafts Gmail replies without sending; `/fact-check` verifies claims and links.
- **Engineering & maintenance:** `/full-review` audits a repository and applies verified fixes; `/smoke` exercises every task and CLI command; `/trim <path>` cuts tokens without losing meaning; `/auth-status` checks CLI logins and prints exact re-login commands; `/task-prompts` writes handoff prompts (resume agy with `agy -c`, compact with `/compact`).

## Credentials

### Authentication & Logins

```bash
dot login                 # This machine's providers (auth.login); opens the browser only when needed
dot login --check         # Report which providers need a login (exit 1 if any)
dot login github          # GitHub
dot login workspace       # Google Workspace
dot login gcp             # Google Cloud and ADC
dot login colab           # ADC with Colab scopes, then verify session access
```

GitHub pushes use SSH even for HTTPS clones (register a key in [GitHub settings](https://github.com/settings/keys)). `dot login` also reconciles GitHub scopes and, when `GWS_PROJECT` or `auth.workspace.project` is set, Workspace APIs and OAuth setup (`dot setup github` or `dot setup workspace <project-id>` runs either alone). Configure per-machine providers in `~/.config/dot.yaml` under `auth.login` (default `[github, gcp, workspace]`; `colab` is opt-in); see the [authentication guide](skills/dot-cli/references/authentication.md).

Agent harnesses manage their own logins (mise locks every harness except self-updating Antigravity):

| Harness     | Command                     | Guide                                              |
| ----------- | --------------------------- | -------------------------------------------------- |
| Antigravity | `agy`                       | [agy](skills/agy/SKILL.md)                         |
| Claude Code | `claude auth login`         | [agent-harnesses](skills/agent-harnesses/SKILL.md) |
| Copilot     | `copilot login`             | [agent-harnesses](skills/agent-harnesses/SKILL.md) |
| OpenCode    | `opencode`, then `/connect` | [agent-harnesses](skills/agent-harnesses/SKILL.md) |

Add optional MCP servers with [mcp-setup](skills/mcp-setup/SKILL.md).

### Commit signing

Each machine signs commits and annotated tags (`git tag NAME -m MSG`) with its own passphraseless Ed25519 SSH key (`~/.ssh/id_ed25519_signing`) so agent shells can sign unattended and any machine can be revoked independently; the private key never enters this repository, and machines without it commit unsigned. A signature proves the machine, not a human. Provision a new machine once (`dot setup github` drops the temporary `write:ssh_signing_key` scope afterwards):

```bash
ssh-keygen -t ed25519 -N '' -C "git-signing@$(hostname)" -f ~/.ssh/id_ed25519_signing
dot login github --grant write:ssh_signing_key
gh ssh-key add ~/.ssh/id_ed25519_signing.pub --type signing --title "$(hostname) signing"
dot setup github
printf '*@fmind.dev namespaces="git" %s\n' "$(cat ~/.ssh/id_ed25519_signing.pub)" >>"$(chezmoi source-path)/dot_config/git/allowed_signers"
chezmoi apply ~/.gitconfig ~/.config/git/allowed_signers
```

Commit the new [`allowed_signers`](dot_config/git/allowed_signers) line so every machine verifies signatures locally (`git log --show-signature`), and once every machine signs, enable [vigilant mode](https://docs.github.com/en/authentication/managing-commit-signature-verification/displaying-verification-statuses-for-all-of-your-commits) in [GitHub keys](https://github.com/settings/keys). To retire a machine, delete its line and GitHub key.

### Secret Management

Secrets are never exported at shell startup:

- **Native credential seeds:** Hugging Face, Kaggle, and OpenCode credentials deploy only when absent so later logins (`hf auth login`, `kaggle auth login`, OpenCode `/connect`) survive apply. For customer work, isolate accounts with the [override guide](skills/dot-cli/references/authentication.md#customer-overrides-and-isolation).
- **Scoped secrets:** pass a personal key to a single command with `dot secret run` (an existing environment value wins, and an empty one fails instead of loading the personal key; see [scoped credentials](skills/dot-cli/references/authentication.md#scoped-credentials)). Personal model integrations default to [GCP Agent Platform with ADC](skills/model-providers/references/gcp-agent-platform.md), OpenCode uses OpenRouter, and PyPI publishes via Trusted Publishing:

  ```bash
  dot secret run OPENROUTER_MANAGEMENT_KEY -- <command>
  ```

- **Encrypted sources:** only the owner's `~/.config/chezmoi/key.txt` decrypts committed `*.age` files; without it, apply skips them. Back up your key and never copy it to a customer-managed machine. Import new secrets with mode `0600` and `chezmoi add --encrypt` (`--create` for native login seeds), never pass secret values in command arguments, and refresh encrypted seeds after rotating native credentials.

## Adapting this

Fork and replace these personal defaults:

1. **Identity:** prompts in [`.chezmoi.toml.tmpl`](.chezmoi.toml.tmpl), the clone URL in [`install.sh`](install.sh), and [`allowed_signers`](dot_config/git/allowed_signers) before adding your [signing key](#commit-signing). Use unmanaged `~/.config/git/config.local` for local Git overrides.
1. **Secrets:** replace the age recipient in [`.chezmoi.toml.tmpl`](.chezmoi.toml.tmpl) and remove or re-encrypt `*.age` sources before applying ([Secret Management](#secret-management)).
1. **Persona:** edit [`dot_agents/AGENTS.md`](dot_agents/AGENTS.md), shared across all harnesses.
1. **Workspaces & trust:** update `pull.directories` (also seeds Claude's `additionalDirectories`), `trust.github_owners`, and `trust.agy_projects` in `~/.config/dot.yaml`, plus personal-checkout `includeIf` paths in [`dot_gitconfig.tmpl`](dot_gitconfig.tmpl). Manage mise trust via `mise trust` or unmanaged `~/.config/mise/conf.d/trust.toml`.
1. **Theme & design:** update [`.chezmoiexternal.toml.tmpl`](.chezmoiexternal.toml.tmpl), pinned to an [fmind/theme](https://github.com/fmind/theme) commit (`mise run upgrade` advances it; personal work only).

## Uninstall / rollback

There is no single uninstaller: record `chezmoi managed`, run `chezmoi purge` (removes source, config, and state while leaving deployed files) and `mise implode --config` (removes mise and its tools), then restore backups and remove remaining deployed files, shell blocks, fonts, and agent state.

To roll back, preserve local edits, check out the previous release tag, and run `mise run full` followed by `mise run vim` to restore locked tools, the CLI, and Neovim plugins. Newer files, application data, and migrations are not rolled back.

## Security

Report vulnerabilities through [SECURITY.md](.github/SECURITY.md).

## License

[MIT](LICENSE) © Médéric Hurier (Fmind)
