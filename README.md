# Dot

My personal dotfiles for **AI-driven, CLI-first development** on Linux and macOS. [Chezmoi](https://www.chezmoi.io/) manages the files; [mise](https://mise.jdx.dev/) manages tools and tasks. Read, borrow, or fork to build your own workstation.

[![CI](https://github.com/fmind/dot/actions/workflows/ci.yml/badge.svg)](https://github.com/fmind/dot/actions/workflows/ci.yml) [![Release](https://img.shields.io/github/v/release/fmind/dot)](https://github.com/fmind/dot/releases/latest) [![License](https://img.shields.io/github/license/fmind/dot)](LICENSE)

[Install](#installation) · [Use](#everyday-use) · [Credentials](#credentials) · [Adapt](#adapting-this)

<a href=".github/assets/dot-overview.svg">
  <img
    src=".github/assets/dot-overview.svg"
    alt="How dot works: clone this repository of dotfiles, persona, skills, tool baseline and encrypted credentials; install.sh bootstraps mise and chezmoi; chezmoi applies files, mise installs locked tools and the dot CLI checks health, so your Linux or macOS workstation gets its terminal, editor, Python, cloud tools and four agent harnesses. Change the source, never the deployed copy."
    width="960"
  >
</a>

## Highlights

- **Terminal:** Fish, Starship, Atuin, zoxide, fzf, Ghostty, and Zellij.
- **Editor:** Neovim with LazyVim, styled with [fmind/theme](https://github.com/fmind/theme).
- **Agents:** Antigravity (the primary harness), Claude Code, Copilot, and OpenCode share a persona and [skills](skills/); `dot agent session sync` archives their local sessions for [usage reports](skills/agent-usage/SKILL.md), and retired Codex and Grok archives stay queryable.
- **Development:** Python with uv, Ruff, ty, and pytest, plus cloud and service CLIs; projects pin their own infrastructure tools.
- **Automation:** the `dot` CLI checks workstation health, manages workspaces, and reports agent usage.

## Prerequisites

| Platform            | Requirements                            | CI coverage                            |
| ------------------- | --------------------------------------- | -------------------------------------- |
| Linux x86-64        | glibc 2.39+ (Debian 13 / Ubuntu 24.04+) | Full repository gate and starter tests |
| macOS Apple Silicon | macOS 15+, Xcode Command Line Tools     | Templates, Python and starter tests    |

The macOS baseline follows [Homebrew's supported versions](https://docs.brew.sh/Installation#macos-requirements). Other platforms are untested. CI checks templates, code, and builds; it does not run the installer end to end.

Install the host prerequisites first; the rest installs in user space:

```bash
# Debian / Ubuntu
sudo apt install -y git curl libatomic1 build-essential gnome-keyring xclip wl-clipboard libnotify-bin
# ChromeOS Linux with GPU acceleration on: let Ghostty open the GPU, then shut down Linux and restart it
sudo usermod -aG render "$USER"

# macOS
xcode-select --install
```

The installer requires mise 2026.10.18 or newer and installs it if absent. [Ghostty](https://ghostty.org/docs/install/binary) is the recommended terminal. A container engine is optional.

## Installation

> [!WARNING]
> These are personal dotfiles: [adapt them](#adapting-this) and back up your files first. Setup overwrites managed files without backups. Agents use broad autonomous permissions, and apply automatically trusts configured workspaces and owner-allowlisted repositories. Review the settings and [trust behavior](skills/dot-cli/references/daily-workflows.md#folder-trust) before use.

Read [`install.sh`](install.sh), then:

```bash
git clone https://github.com/fmind/dot.git ~/.local/share/chezmoi
bash ~/.local/share/chezmoi/install.sh
```

Enter **your own** Git name, email, personal-repository email, and GitHub username when prompted; the defaults are mine. Open a new shell and run `dot doctor` to check the installation.

To resume interrupted setup, rerun the installer. Set `SKIP_GIT_PULL=true` to use an existing checkout without fetching upstream. From an initialized checkout, `mise run full` reapplies files and synchronizes locked tools, `dot`, and completions.

### Shell

Ghostty and Zellij launch Fish; your login shell stays unchanged. Fish attaches to Zellij once at startup and returns to a shell when Zellij exits or detaches. In another terminal, run `fish` or set its shell command to `~/.local/share/mise/shims/fish`.

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

The [Dot CLI guide](skills/dot-cli/SKILL.md) covers commands, diagnostics, and recovery.

Fish shortcuts: `h` runs `dot`, `hd` doctor, `hh` headroom, `hs` repositories needing attention (with fetch), `hp` pull, `ho` orphans, `hc` caches, and `ha` agent statistics.

In Neovim, `<leader>gm` toggles the current buffer's Git comparison between the index and the default branch's merge-base; other buffers keep their own comparison. Tab accepts completions and Enter always inserts a newline; in Markdown, text, commit-message, and unnamed buffers, Enter continues or splits list items, and on an empty item it outdents or ends the list. Clipboard selection uses macOS's native provider, or xclip when Linux has an X display; Wayland-only sessions use Neovim's native detection. mise config files get diagnostics, completion, and hover from `mise lsp`.

Zellij tiles new panes (`Alt n`) as equal columns, up to four, to suit wide screens such as 21:9 or 32:9 glasses; a fifth pane, or `Ctrl b`, `Space`, switches to a half-stacked arrangement for narrow screens. Restored sessions keep their saved layouts, and the Fish wrapper saves background (`attach -b`) and killed (`kill-session`) sessions so one-pane directory sessions stay resurrectable. On ChromeOS, `Alt [` and `Alt ]` snap windows to the left or right half and never reach Zellij; on a 32:9 screen, each half is about one 16:9 display.

### Dot configuration

Machine-local settings live in `~/.config/dot.yaml` and merge with [built-in defaults](dot/src/fmind_dot/config.py). dot reads the file named by `dot --config <path>`, else `DOT_CONFIG_PATH`, else the default path. A missing default file is fine; a missing explicitly selected file is an error. An unreadable file always fails instead of falling back to defaults.

Use `dot config edit` to edit settings; it validates them when the editor exits. Alternate `~/.config/dot.*.yaml` profiles are loaded only when selected; these files stay outside Git and chezmoi management.

### Usage reports

Usage reports distinguish token counts and estimated API value from actual costs; `dot agent stats --monthly` groups them by UTC calendar month. See the [usage guide](skills/agent-usage/SKILL.md).

Session capture preserves longer archived transcripts and recorded usage. An unreadable archive fails for that agent while other agents continue; archive queries fail when a directory is inaccessible instead of reporting no sessions. Restore access before retrying.

## Repository tasks

Run these from the checkout; `mise tasks` lists every task and alias.

| Command            | Purpose                                                                                    |
| ------------------ | ------------------------------------------------------------------------------------------ |
| `mise run diff`    | Preview dotfile changes                                                                    |
| `mise run apply`   | Apply files and eligible hooks                                                             |
| `mise run doctor`  | Check workstation health (`dot`, chezmoi, and mise)                                        |
| `mise run full`    | Synchronize files, locked tools, CLI, and completions; retire old lock graphs and installs |
| `mise run upgrade` | Upgrade dependencies, tools, the theme pin, and plugins (includes `full`)                  |
| `mise run all`     | Format, check, test, and build the repository                                              |

`all` rewrites formatting but does not deploy. Contributor details: [AGENTS.md](AGENTS.md), [verification](.agents/skills/dot-verify/SKILL.md), and [releases](.agents/skills/dot-release/SKILL.md).

Python follows the latest 3.14 patch release until the required tools ship Python 3.15 wheels.

## Agent layer

<a href=".github/assets/agent-layer.svg">
  <img
    src=".github/assets/agent-layer.svg"
    alt="One agent layer for four harnesses: the persona, skill catalog and per-host settings are written once in this repository, deployed by chezmoi to Antigravity, Claude Code, GitHub Copilot and OpenCode; dot agent session sync archives their sessions and dot agent stats reports usage."
    width="960"
  >
</a>

Antigravity, Claude Code, Copilot, and OpenCode share one persona and one skill catalog. Launch agy from Fish or Zellij (`Alt a`): its wrapper puts mise shims first so agent commands follow each project's tool pins. No custom subagent roles are deployed: each host's general-purpose subagents load the same persona and skills. See [cross-harness agents](skills/agent-project/references/cross-harness-agents.md) before adding one.

## Agent skills

Setup links this repository's [`skills/`](skills/) into `~/.agents/skills/`, alongside independently installed packages. Restart agent sessions after catalog changes. See [skill authoring](skills/skillify/SKILL.md) and [catalog maintenance](.agents/skills/dot-skills/SKILL.md); upgrades from older releases may need the [retired-link cleanup](.agents/skills/dot-skills/references/installed-links.md#retired-links).

Use `/clipboard` to copy the requested deliverable from the preceding exchange, or `/clipboard <selection>` to choose a result. The [clipboard skill](skills/clipboard/SKILL.md) verifies the copied text using native macOS or ChromeOS/Linux tools.

Other everyday shortcuts: `/full-review` reviews a whole project and applies verified fixes, `/smoke` runs every task and CLI command, `/trim <path>` shortens without losing meaning, `/auth-status` lists expired logins with the exact re-login command, and `/task-prompts` writes delegation or continuation prompts (resume agy with `agy -c`, compact with `/compact`). For writing, `/stakeholder-writing` turns results into reports, proposals, and updates that busy readers can act on, `/draft-mail` creates Gmail drafts only, and `/fact-check` verifies claims and links.

## Credentials

### Authentication & Logins

```bash
dot login                 # This machine's providers (auth.login); skips what is ready, opens the browser when needed
dot login --check         # Only report which providers need a login (exit 1 if any)
dot login github          # GitHub
dot login workspace       # Google Workspace
dot login gcp             # Google Cloud and ADC
dot login colab           # ADC with Colab scopes, then verify session access
```

GitHub pushes use SSH, even for HTTPS clones: register an SSH key in [GitHub settings](https://github.com/settings/keys). `dot login` also reconciles GitHub scopes and, when `GWS_PROJECT` or `auth.workspace.project` is set, Workspace APIs and OAuth setup; run `dot setup github` or `dot setup workspace <project-id>` for one step alone. Credential lifetimes follow each account's session policy, so each machine lists its providers in its unmanaged `~/.config/dot.yaml`, for example `auth: {login: [gcp, workspace]}`; the default is `[github, gcp, workspace]` and `colab` is opt-in. Account selection and scope policy live in the [authentication guide](skills/dot-cli/references/authentication.md).

Agent harnesses use their own logins:

| Harness     | Command                     |
| ----------- | --------------------------- |
| Antigravity | `agy`                       |
| Claude Code | `claude auth login`         |
| Copilot     | `copilot login`             |
| OpenCode    | `opencode`, then `/connect` |

For hooks, notifications, and provider overrides, see [agent harnesses](skills/agent-harnesses/SKILL.md) and [Antigravity](skills/agy/SKILL.md). Add optional MCP servers with [mcp-setup](skills/mcp-setup/SKILL.md).

mise installs and locks every harness except Antigravity, which updates itself.

### Commit signing

Each machine signs commits and annotated tags (`git tag NAME -m MSG`) with its own Ed25519 SSH key, so one machine can be revoked without touching the others; the private key never enters this repository, even encrypted. Apply enables signing only where `~/.ssh/id_ed25519_signing` exists, and a machine without it commits unsigned. The key has no passphrase so agent shells sign unattended: a signature proves the machine, not a human. Set up a new machine once; uploading the key takes a one-off `write:ssh_signing_key` grant, which `dot setup github` removes afterwards so a stolen token cannot add keys:

```bash
ssh-keygen -t ed25519 -N '' -C "git-signing@$(hostname)" -f ~/.ssh/id_ed25519_signing
dot login github --grant write:ssh_signing_key
gh ssh-key add ~/.ssh/id_ed25519_signing.pub --type signing --title "$(hostname) signing"
dot setup github
printf '*@fmind.dev namespaces="git" %s\n' "$(cat ~/.ssh/id_ed25519_signing.pub)" >>"$(chezmoi source-path)/dot_config/git/allowed_signers"
chezmoi apply ~/.gitconfig ~/.config/git/allowed_signers
```

Commit the new [`allowed_signers`](dot_config/git/allowed_signers) line so every machine verifies the others locally (`git log --show-signature`). Retire a machine by deleting its line and its key in [GitHub SSH and GPG keys](https://github.com/settings/keys). Turn on [vigilant mode](https://docs.github.com/en/authentication/managing-commit-signature-verification/displaying-verification-statuses-for-all-of-your-commits) there once every machine signs, so unsigned commits under your name show as Unverified. GitHub verifies only classical signatures (GPG, SSH, S/MIME), and a verified commit keeps its status after key rotation, so post-quantum signing waits for GitHub support.

### Secret Management

Secrets are not exported at shell startup. Hugging Face, Kaggle, and OpenCode use native credential files, seeded only when absent so later logins survive apply. Use `hf auth login`, `kaggle auth login`, or OpenCode's `/connect` for your own accounts. For customer work, select credentials explicitly using the [account override guide](skills/dot-cli/references/authentication.md#customer-overrides-and-isolation).

Supply a personal key to one command with `dot secret run`; PyPI packages publish through Trusted Publishing, not a personal token. Personal model integrations default to [GCP Agent Platform with ADC](skills/model-providers/references/gcp-agent-platform.md); OpenCode uses OpenRouter.

```bash
dot secret run STITCH_ACCESS_TOKEN -- <command>
```

The helper preserves existing environment values; an empty value fails instead of loading the personal key. See [scoped credentials](skills/dot-cli/references/authentication.md#scoped-credentials) for supported keys and precedence.

**Encrypted sources:** only the owner's age key decrypts the committed credentials. Without `~/.config/chezmoi/key.txt`, apply skips them; a different key fails decryption. Back up your key. To capture a credential, set its file mode to `0600` and use `chezmoi add --encrypt` (`--create` for native login seeds). Never put secret values in command arguments. Rotate native credentials through their tool and refresh the encrypted seed separately.

## Adapting this

Fork and replace these personal defaults:

1. **Identity:** prompts in [`.chezmoi.toml.tmpl`](.chezmoi.toml.tmpl) and the clone URL in [`install.sh`](install.sh). Use unmanaged `~/.config/git/config.local` for Git overrides and `includeIf` profiles. Replace [`allowed_signers`](dot_config/git/allowed_signers) and its `*@fmind.dev` principal before adding your own [signing key](#commit-signing).
1. **Secrets:** replace the age recipient and remove or re-encrypt credential sources before applying; see [Secret Management](#secret-management).
1. **Persona:** edit [`dot_agents/AGENTS.md`](dot_agents/AGENTS.md), which every harness loads.
1. **Workspaces:** change `pull.directories`, `trust.github_owners`, and `trust.agy_projects_exclude` (repositories kept out of agy's Remote Control picker) in `~/.config/dot.yaml`, plus Claude's directories in [`dot_claude/modify_private_settings.json`](dot_claude/modify_private_settings.json) and the personal-checkout `includeIf` directories in [`dot_gitconfig.tmpl`](dot_gitconfig.tmpl), which commit with the personal-repository email. Mise trust is separate: use `mise trust /path/to/mise.toml` or unmanaged `~/.config/mise/conf.d/trust.toml`.
1. **Theme and design:** change [`.chezmoiexternal.toml.tmpl`](.chezmoiexternal.toml.tmpl); theme files and the [`DESIGN.md`](https://github.com/fmind/theme/blob/main/DESIGN.md) design system deployed to `~/.agents/DESIGN.md` are pinned to an [fmind/theme](https://github.com/fmind/theme) commit that `mise run upgrade` advances. The persona makes it the default for personal work, never for customer work.

## Uninstall / rollback

There is no complete uninstaller. Record `chezmoi managed` before removing state: `chezmoi purge` removes chezmoi's source, configuration, and state but leaves deployed files. `mise implode --config` removes mise and its tools. Restore your backups and remove remaining deployed files, shell integration blocks, separately installed CLIs, fonts, and agent data as needed.

To roll back, preserve local edits, check out the previous release tag, and run `mise run full`, then `mise run vim` to restore locked Neovim plugins. Applying files alone does not reinstall previous tool or CLI versions. Newer files, application data, and migrations are not rolled back.

## Security

Report vulnerabilities through [SECURITY.md](.github/SECURITY.md).

## License

[MIT](LICENSE) © Médéric Hurier (Fmind)
