# Dot

My personal dotfiles for **AI-driven, CLI-first** development on Linux and macOS. Declarative, reproducible, and fast.

Managed with [chezmoi](https://www.chezmoi.io/) (files) and [mise](https://mise.jdx.dev/) (tools & tasks).

> [!IMPORTANT]
> Personal, opinionated dotfiles. Review before running; provided **as-is** without warranty (see [LICENSE](LICENSE)).

## Highlights

- **Shell & Terminal** — [Fish](https://fishshell.com/) with [Starship](https://starship.rs/), [Atuin](https://atuin.sh/), [zoxide](https://github.com/ajeetdsouza/zoxide), [fzf](https://github.com/junegunn/fzf), [Ghostty](https://ghostty.org/), and [Zellij](https://zellij.dev/).
- **Editor** — [Neovim](https://neovim.io/) powered by [LazyVim](https://www.lazyvim.org/).
- **AI Harnesses & Skills** — Shared persona (`AGENTS.md`) and [Agent Skills](https://agentskills.io) ([`skills/`](skills/)) for [Antigravity](https://antigravity.google/) (`agy`), [Claude Code](https://claude.com/claude-code), [OpenAI Codex](https://developers.openai.com/codex/) (`codex`), [OpenCode](https://opencode.ai/), [GitHub Copilot](https://github.com/features/copilot), [Grok Build](https://x.ai/build) (`grok`), and [Cursor CLI](https://cursor.com/docs/cli) (`cursor-agent`).
- **Python & Cloud Stack** — Typed Python with uv, Ruff, ty, pytest, marimo, Django, Litestar, and Google ADK, plus OpenTofu for infrastructure.
- **`dot` CLI** — Typed Python tool for workspace automation, health checks, session archives, and diagnostics ([`dot/`](dot/)).
- **User-Space Toolchain** — CLIs managed declaratively in user space via [mise](https://mise.jdx.dev/) and dotfiles synced via [chezmoi](https://www.chezmoi.io/).

## Prerequisites

Tool lockfiles target Linux x86-64 and macOS Apple Silicon. The installer requires mise 2026.9.1 or newer; it installs mise when absent but stops if an existing version is too old.

### Host Packages

The bootstrap installs user-space tools via mise, but requires host build tools, Git, curl, and native credential storage:

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

- **Terminal & Font**: [Ghostty](https://ghostty.org/docs/install/binary) and [FiraCode Nerd Font Mono](https://www.nerdfonts.com/font-downloads).
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

The installer prompts for Git identity, applies the dotfiles and eligible installation hooks, installs the locked tools and `dot` CLI, and configures Git hooks and Neovim plugins. Open a new shell afterward, or use `~/.local/bin/dot --help` to check the installed CLI directly.

### Python environment

Run `uv sync --locked` in each existing Python project to create its `.venv` before opening it in Neovim. LazyVim uses ty for types and navigation, Ruff for linting, formatting, and import sorting, and the project environment for pytest and debugging. mise supplies ty and Ruff ahead of Mason's tools. Python debugging uses uv to provide debugpy on demand; the first run may download it.

For a Python REPL with the project's dependencies, run `uv run --with ptpython ptpython` from that project. The globally installed `ptpython` has its own isolated environment.

### Cursor CLI

Cursor CLI is installed by mise as `cursor-agent`. Create a Cursor account, then run `cursor-agent login`; installation and local configuration work before sign-in. The managed CLI configuration enables unrestricted approvals, disables sandboxing, enables Vim controls and detailed progress, and disables commit/PR attribution. Your account-selected model and explicit deny rules are retained. Global skills load from `~/.agents/skills`; a session-start hook supplies the shared persona. Cursor uses the terminal palette; no unsupported theme key is set. Account-dependent models and inference remain unverified until login.

### Dot configuration

The CLI optionally reads `~/.config/dot.yaml` and merges its values with built-in defaults. The [CLI configuration guide](dot/README.md) describes version 3 and its numeric timeout settings. Select another file with `DOT_CONFIG_PATH` or `dot --config <path>`; the explicit flag takes precedence. A missing default file uses built-in defaults, while a missing explicitly selected file is an error.

Use `dot config show` to inspect effective settings, `dot config validate` to check them, and `dot config edit` to edit the file (through its source when chezmoi manages it). Command help and the [Dot CLI guide](skills/dot-cli/SKILL.md) describe available operations.

## Agent skills

Skills use the standard `~/.agents/skills/` directory. Dotfiles setup creates a real directory and links each package from this repository's [`skills/`](skills/) catalog into it. Other packages can be directories or individual links in the same location; names must be unique. Packages in this catalog may reference sibling skills, so check dependencies before copying one folder on its own.

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

| Tool / Service           | Command                                           | Auth Type               |
| ------------------------ | ------------------------------------------------- | ----------------------- |
| **GitHub CLI**           | `gh auth login`                                   | Browser OAuth           |
| **Google Cloud SDK**     | `gcloud auth login --update-adc`                  | ADC + OAuth             |
| **Google Workspace CLI** | `gws auth login`                                  | Browser OAuth           |
| **Antigravity CLI**      | `agy`                                             | On-demand prompt        |
| **Claude Code**          | `claude auth login` (or `claude` → `/login`)      | Interactive / browser   |
| **Cursor CLI**           | `cursor-agent login`                              | Create an account first |
| **OpenAI Codex CLI**     | `codex login`                                     | Interactive             |
| **OpenCode CLI**         | `gcloud auth login --update-adc`, then `opencode` | Vertex AI ADC           |
| **GitHub Copilot CLI**   | `copilot login` (or `copilot` → `/login`)         | Interactive / browser   |
| **Grok Build CLI**       | `grok login` (or `XAI_API_KEY`)                   | Interactive / API key   |
| **Jules CLI**            | `jules login`                                     | Interactive             |

Use `gh auth refresh` for explicitly required GitHub scopes, and `gws auth setup --project <project-id>` for Workspace setup. Select the account, project, APIs, and scopes deliberately through each provider's native CLI.

Define PATs or session tokens for workspace MCP integrations on demand: `AIRTABLE_PAT`, `GITHUB_PERSONAL_ACCESS_TOKEN`, `DATABRICKS_HOST` / `DATABRICKS_TOKEN`, and `JIRA_URL` / `JIRA_USERNAME` / `JIRA_API_TOKEN`.

## License

[MIT](LICENSE) © Médéric Hurier (Fmind)
