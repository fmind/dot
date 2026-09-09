# Dot

My personal dotfiles for **AI-driven, CLI-first** development on Linux and macOS. Declarative, reproducible, and fast.

Managed with [chezmoi](https://www.chezmoi.io/) (files) and [mise](https://mise.jdx.dev/) (tools & tasks).

> [!IMPORTANT]
> Personal, opinionated dotfiles. Review before running; provided **as-is** without warranty (see [LICENSE](LICENSE)).

## Highlights

- **Shell & Terminal** — [Fish](https://fishshell.com/) with [Starship](https://starship.rs/), [Atuin](https://atuin.sh/), [zoxide](https://github.com/ajeetdsouza/zoxide), [fzf](https://github.com/junegunn/fzf), [Ghostty](https://ghostty.org/), and [Zellij](https://zellij.dev/).
- **Editor** — [Neovim](https://neovim.io/) powered by [LazyVim](https://www.lazyvim.org/).
- **AI Harnesses & Skills** — Shared persona (`AGENTS.md`) and [Agent Skills](https://agentskills.io) ([`skills/`](skills/)) for [Antigravity](https://antigravity.google/) (`agy`), [Claude Code](https://claude.com/claude-code), [OpenAI Codex](https://developers.openai.com/codex/) (`codex`), [OpenCode](https://opencode.ai/), [GitHub Copilot](https://github.com/features/copilot), and [Grok Build](https://x.ai/build) (`grok`).
- **Python & Cloud Stack** — Typed Python with uv, Ruff, ty, pytest, marimo, Django, Litestar, and Google ADK, plus OpenTofu for infrastructure.
- **`dot` CLI** — Typed Python tool for workspace automation, health checks, session archives, and logins ([`dot/`](dot/)).
- **User-Space Toolchain** — CLIs managed declaratively in user space via [mise](https://mise.jdx.dev/) and dotfiles synced via [chezmoi](https://www.chezmoi.io/).

## Prerequisites

### Host Packages

The bootstrap installs user-space tools via mise, but requires host build tools, Git, curl, and native credential storage:

```bash
# Linux (Debian/Ubuntu)
sudo apt install -y git curl libatomic1 build-essential gnome-keyring

# macOS
xcode-select --install
```

### GitHub Authentication

Generate an SSH key and register the public key in [GitHub Settings Keys](https://github.com/settings/keys):

```bash
ssh-keygen -t ed25519 -a 100 -C "your_email@example.com"
```

### Recommended Tools (Optional)

- **Terminal & Font**: [Ghostty](https://ghostty.org/docs/install/binary) and [FiraCode Nerd Font Mono](https://www.nerdfonts.com/font-downloads).
- **Containers**: A Docker-compatible container engine (Docker or Podman) if building container images.

## Installation

```bash
# Clone into the chezmoi source directory
git clone https://github.com/fmind/dot.git ~/.local/share/chezmoi

# Run the installer
bash ~/.local/share/chezmoi/install.sh
```

Set `SKIP_GIT_PULL=true` if bootstrapping from an existing local checkout without fetching upstream.

> [!WARNING]
> Agent configurations default to autonomous execution with broad permissions. Use in trusted workspaces and review each harness's settings before use.

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

| Tool / Service           | Command                                               | Auth Type             |
| ------------------------ | ----------------------------------------------------- | --------------------- |
| **GitHub CLI**           | `dot login github` (or `gh auth login`)               | Browser OAuth         |
| **Google Cloud SDK**     | `dot login gcp` (or `gcloud auth login --update-adc`) | ADC + OAuth           |
| **Google Workspace CLI** | `dot login workspace`                                 | Browser OAuth         |
| **Antigravity CLI**      | `agy`                                                 | On-demand prompt      |
| **Claude Code**          | `claude` → `/login`                                   | Interactive / browser |
| **OpenAI Codex CLI**     | `codex login`                                         | Interactive           |
| **OpenCode CLI**         | `dot login gcp`, then `opencode`                      | Vertex AI ADC         |
| **GitHub Copilot CLI**   | `copilot` → `/login`                                  | Interactive / browser |
| **Grok Build CLI**       | `grok login` (or `XAI_API_KEY`)                       | Interactive / API key |
| **Jules CLI**            | `jules auth login`                                    | Interactive           |

Use `dot setup github` to refresh the configured GitHub OAuth scopes, and `dot setup workspace <project-id>` to enable and configure the Workspace APIs.

Define PATs or session tokens for workspace MCP integrations on demand: `AIRTABLE_PAT`, `GITHUB_PERSONAL_ACCESS_TOKEN`, `DATABRICKS_HOST` / `DATABRICKS_TOKEN`, and `JIRA_URL` / `JIRA_USERNAME` / `JIRA_API_TOKEN`.

## License

[MIT](LICENSE) © Médéric Hurier (Fmind)
