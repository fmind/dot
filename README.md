# Dot

My personal dotfiles for **AI-driven, CLI-first** development on Linux and Mac OS. Declarative, reproducible, and fast.

Managed with [chezmoi](https://www.chezmoi.io/) (files) and [mise](https://mise.jdx.dev/) (tools & tasks).

> [!IMPORTANT]
> These are my personal dotfiles, shared in case they're useful. Feel free to fork and adapt them—but read before you run: they are opinionated and tailored to my workflow. Provided **as-is**, without warranty (see [LICENSE](LICENSE)).

## Highlights

- **Shell** — [Fish](https://fishshell.com/) with [Starship](https://starship.rs/) prompt, [Atuin](https://atuin.sh/) history, [zoxide](https://github.com/ajeetdsouza/zoxide), and [fzf](https://github.com/junegunn/fzf).
- **Editor** — [Neovim](https://neovim.io/) powered by [LazyVim](https://www.lazyvim.org/).
- **Terminal** — [Ghostty](https://ghostty.org/) (GPU-accelerated) and [Zellij](https://zellij.dev/) workspace multiplexer.
- **AI-CLI Integration** — Built-in setups for [OpenAI Codex](https://developers.openai.com/codex/) (`codex`), [Antigravity](https://antigravity.google/) (`agy`), [OpenCode](https://opencode.ai/), [Claude Code](https://claude.com/claude-code), [GitHub Copilot](https://github.com/features/copilot) (`copilot`), and [Grok Build](https://x.ai/build) (`grok`), sharing a unified persona (`AGENTS.md`) and skills.
- **Agent Skills** — A library of reusable [Agent Skills](https://agentskills.io) in [`skills/`](skills/), shared by every AI CLI above.
- **Languages & Stacks** — Go and Python as the core languages, TypeScript with [Angular](https://angular.dev/) and [Firebase](https://firebase.google.com/) for web apps, [Google ADK](https://google.github.io/adk-docs/) for agents, plus OpenTofu/Terraform for infrastructure, [Typst](https://typst.app/) for documents, and [Hugo](https://gohugo.io/) for sites — each with a pinned toolchain, formatter, linter, and test gate.
- **Custom `dot` CLI** — A Go utility for environment health checks, workspace updates, agent session and usage archives, project cleanup, commit generation, and logins. Source in [`dot/`](dot/).
- **User-space toolchain** — `install.sh` bootstraps mise and chezmoi, while a single mise config (`~/.config/mise/config.toml`) pins and manages the development CLI toolchain without system package managers. The committed lock selects exact versions and records artifact digests where the backend supplies them; digest-free backends and live vendor installers remain explicit exceptions.

## Prerequisites

The development CLI toolchain is installed in user space, but the bootstrap still needs Git, curl, host build tools, and native credential storage:

```bash
# Linux (Debian/Ubuntu) — build tools and secret storage keyring
sudo apt install -y git curl libatomic1 build-essential gnome-keyring

# macOS — Git, curl, compilers, and system headers
xcode-select --install
```

Install a Docker-compatible engine if you plan to build container images. Cloud Run is the default deployment target; projects that adopt Kubernetes own and pin their cluster tooling locally. The optional Kubernetes shell shortcuts, editor support, and tool settings remain available for those projects.

The global toolchain covers everyday shell tools, language tooling, and agent CLIs. Install Slidev, LikeC4, Lighthouse, and TypeScript's Genkit CLI in the projects that use them with pnpm; Atlas and Go/Python's Genkit CLI belong in the project's `mise.toml`. Commit the corresponding project lockfiles so dependency fixes travel with the project.

[Ghostty](https://ghostty.org/docs/install/binary) and [FiraCode Nerd Font Mono](https://www.nerdfonts.com/font-downloads) are recommended host integrations for the configured terminal experience; they are not installed by mise.

Generate an SSH key for GitHub authentication:

```bash
ssh-keygen -t ed25519 -a 100 -C "your_email@example.com"
```

> [!TIP]
> Register the public key at [GitHub Settings Keys](https://github.com/settings/keys).

## Installation

```bash
# 1. Clone into the chezmoi source directory
git clone https://github.com/fmind/dot.git ~/.local/share/chezmoi

# 2. Run the installer (mise → chezmoi → apply → tools and integrations)
bash ~/.local/share/chezmoi/install.sh
```

Set `SKIP_GIT_PULL=true` only when intentionally bootstrapping from the existing local checkout without fetching its upstream branch.

The agent configurations enable autonomous execution with broad tool permissions and selected experimental features. Use them in trusted workspaces; review each harness's permission settings before adopting these defaults. Shared instructions guide agent behavior but do not enforce a sandbox.

The installer is idempotent: it keeps an already-installed `mise` and `chezmoi`, and otherwise installs mise from its vendor's install script and chezmoi through mise. The mise lock selects exact versions for x86-64 Linux and Apple silicon macOS and verifies recorded checksums, but registry, Cargo, Go, npm, and pipx entries do not all carry artifact digests. A checksum proves artifact integrity, not publisher identity; provenance verification remains disabled until a tool has a proven signer contract on both platforms. Antigravity and Grok are additional live vendor-script installs outside the mise lock, so reruns converge operationally rather than reproducing those installer bytes.

Tree-sitter builds from source with a minimal mise-managed Rust toolchain so current Neovim parsers work on Linux distributions whose GLIBC cannot run upstream's prebuilt CLI. The first installation takes a few minutes and requires a C compiler and linker, as do Neovim's parser builds.

## Credentials

### Secret Management

API keys and credentials are split between two Fish configuration files:

1. **`~/.config/fish/conf.d/secrets.fish`** (shared, encrypted in repo): Decrypted automatically from `encrypted_private_secrets.fish.age`. Out of the box, it exports:
   - `HUGGINGFACE_API_TOKEN` (Hugging Face API)
   - `JULES_API_KEY` (Jules CLI)
   - `KAGGLE_API_TOKEN` (Kaggle API)
   - `STITCH_ACCESS_TOKEN` (Stitch MCP)
   - `STUDIO_API_KEY` (Gemini API)
   - `UV_PUBLISH_TOKEN` (PyPI package publishing token)

   To decrypt it on apply, provision your private age key:

   ```bash
   mkdir -p ~/.config/chezmoi
   # Place your private key in key.txt and secure its permissions
   chmod 600 ~/.config/chezmoi/key.txt
   ```

   > [!NOTE]
   > If the private key file is not present, `secrets.fish` is automatically ignored during `chezmoi apply` via `.chezmoiignore`. This allows you to bootstrap and run `dot` without decrypting fmind's personal secrets.

   > [!WARNING]
   > **Back up `~/.config/chezmoi/key.txt`.** It is **not** managed by chezmoi. If lost, encrypted repo files are unrecoverable.

1. **`~/.private.fish`** (local, untracked): Sourced automatically by `config.fish` for machine/project overrides. You should manually configure variables here:
   ```fish
   set -gx ANTIGRAVITY_CLOUD_PROJECT   "my-vertex-project"     # Antigravity GCP Project
   set -gx ANTIGRAVITY_CLOUD_LOCATION  "global"                # Antigravity GCP Location
   set -gx OPENCODE_GCP_PROJECT       "my-vertex-project"     # OpenCode Vertex GCP Project
   set -gx GWS_PROJECT                "my-workspace-project"  # Workspace CLI Project
   ```

### OAuth Web Logins

Authenticate these interactive command-line tools once via browser-based OAuth flows:

- **GitHub CLI**: `dot login github` (or `gh auth login`)
- **Google Cloud SDK**: `dot login gcp` (or `clog` / `gcloud auth login --update-adc`)
- **Google Workspace CLI**: `dot login workspace`
- **Google Apps Script**: `dot login clasp` (or `clasp login`)

### On-Demand Logins

Logins and session tokens initialized on demand or configured via local/workspace environment variables:

- **Antigravity CLI**: `agy` (authenticates on-demand during use)
- **OpenAI Codex CLI**: `codex login` (or authenticate on-demand during use)
- **Claude Code**: start `claude`, then run `/login` when authentication is required
- **GitHub Copilot CLI**: start `copilot`, then run `/login` when authentication is required
- **Grok Build CLI**: `grok login` (or set `XAI_API_KEY` for headless runs)
- **Jules CLI**: `jules auth login`
- **Workspace MCP Integrations**: Define PATs/tokens on-demand for workspace configurations:
  - `AIRTABLE_PAT` (Airtable)
  - `JIRA_URL` / `JIRA_USERNAME` / `JIRA_API_TOKEN` (Jira)
  - `DATABRICKS_HOST` / `DATABRICKS_TOKEN` (Databricks)
  - `GITHUB_PERSONAL_ACCESS_TOKEN` (GitHub)

## License

[MIT](LICENSE) © Médéric Hurier (Fmind)
