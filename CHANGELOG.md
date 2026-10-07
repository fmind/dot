# Changelog

All notable changes to this project are documented in this file.

## [11.0.1] - 2026-10-07

### 🐛 Bug Fixes

- _(fish)_ Preserve Darwin Homebrew path precedence over /usr/local/bin (#103)

### 📚 Documentation

- _(skills)_ Align bf with Brain Framework 18.3.0

### 🧹 Miscellaneous

- _(deps)_ Lock Brain Framework 18.3.0

## [11.0.0] - 2026-10-07

### 🚀 Features

- _(nvim)_ Switch to native Copilot, live Markdown preview, and git base keymaps
- _(git)_ Add a dt alias for Neovim's directory difftool
- _(cli)_ [**breaking**] Add login --check, status --fetch, and agent-facing help contracts
- _(agent)_ [**breaking**] Count OpenCode steps and model requests with parser 11 and a shared host registry

### ♻️ Refactor

- _(system)_ Unify the cache and prune registry and group nested orphans

### 📚 Documentation

- _(skills)_ Tighten the catalog and refresh tool guidance

### 🧪 Testing

- _(delegate-tasks)_ Outlast the kill grace in the leaked-grandchild check

### ⚙️ Build & CI

- _(tasks)_ Gate releases on network scans and verify every lock entry

### 🧹 Miscellaneous

- _(security)_ Accept the cf lock's sharp advisory until miniflare upgrades
- Format the v10.1.2 changelog
- _(deps)_ Upgrade mise tools and Python dependencies
- _(mise)_ Disable agents-cli usage telemetry

## [10.1.2] - 2026-10-06

### ♻️ Refactor

- _(skills)_ Fold containerize into docker and update-ignores into repository-maintenance
- _(agents)_ Keep four shared roles in exact agent directories
- _(deploy)_ Install the dot CLI with uv tool install

### 📚 Documentation

- _(skills)_ Keep image pins in project locks and drop the dot command table
- Trim the persona, project rules, and redundant README illustrations
- _(skills)_ Mirror the bf-action skill of Brain Framework 18.2.0

### 🧪 Testing

- Deflake the chezmoi fixture and archive lock race

### 🧹 Miscellaneous

- _(shell)_ Simplify editor, pager, ignore, and database preset config
- _(deps)_ Upgrade typer, workstation tools, and Neovim plugins
- _(deps)_ Lock Brain Framework 18.2.0

## [10.1.1] - 2026-10-06

### 🐛 Bug Fixes

- Support custom meminfo on darwin and deflake agy test timeout
- _(security)_ Keep SSH, gws, and cloud credentials out of searches
- _(agy)_ Merge user hooks and reload systemd drop-ins on change
- _(config)_ Ignore .DS_Store globally and let gh use nvim-tty
- _(hooks)_ Format the editor wrapper on commit
- _(delegate-tasks)_ Keep the canceled state when a worker ignores SIGTERM
- _(dot)_ Name the move-aside step for unreadable transcripts
- _(skills)_ Name missing guide markers instead of a no-op fix
- _(skills)_ Correct stale commands, policies, and template defaults

### 📚 Documentation

- _(skills)_ Trim duplicated archive and pin guidance

### 🧪 Testing

- Deflake timing-bound tests and drop dead fixtures

### 🧹 Miscellaneous

- _(deps)_ Upgrade usage, a neovim plugin, and template pins

## [10.1.0] - 2026-10-06

### 🚀 Features

- Add cache/trust JSON, doctor discovery, and agent shell defaults
- _(doctor)_ Report caller-environment checks as non-failing notes
- Fail fast instead of opening nvim without a terminal

### 🧹 Miscellaneous

- Drop release-age cooldowns from npm, Dependabot, and skills
- _(deps)_ Upgrade tools, theme pin, and editor plugins

## [10.0.0] - 2026-10-05

### ♻️ Refactor

- [**breaking**] Trim unused commands, release publishing, and gates
- Lead rules with bold summaries and open subagent roles

## [9.0.3] - 2026-10-04

### 🐛 Bug Fixes

- _(auth)_ Copy the GitHub device code through X11 on Crostini
- _(codex)_ Leave a converged config in the layout Codex wrote

## [9.0.2] - 2026-10-04

### 🐛 Bug Fixes

- _(skills)_ Publish the Python starter through Trusted Publishing only

### 🧹 Miscellaneous

- _(config)_ Retire removal markers that every workstation applied
- _(secrets)_ Retire the unused JULES_API_KEY seed

## [9.0.1] - 2026-10-04

### 🐛 Bug Fixes

- _(git)_ Match the chezmoi source include through symlinked paths

## [9.0.0] - 2026-10-04

### 🚀 Features

- _(secrets)_ [**breaking**] Retire dot secret publish and the personal PyPI token
- _(auth)_ Own brain-sensor Workspace scopes and flag plaintext gh tokens
- _(git)_ Commit personal checkouts with the personal email
- _(agents)_ Register the brain SessionStart hook for Claude and Codex
- _(archive)_ Resolve agy workspaces, follow archived Codex rollouts, and prove current transcripts

### 🐛 Bug Fixes

- _(cli)_ Report Cancelled. on interrupted commands and drop dead Copilot doctor branches
- _(fish)_ Export the fzf theme only once chezmoi fetched it

### 📚 Documentation

- _(skills)_ Correct stale commands, links, and tool contracts

### 🧪 Testing

- _(release)_ Keep release wait tests with the release suite

### ⚙️ Build & CI

- _(cd)_ Gate releases on macOS tests and outlast the publish bounds
- _(mise)_ Require mise 2026.10.2 and lock template formatters

## [8.4.0] - 2026-10-04

### 🚀 Features

- _(cache)_ Label each provider in a multi-provider report
- _(agent)_ Fail context checks on duplicate skill names
- _(skills)_ Optimize the catalog and give colliding skills unique names

### 🐛 Bug Fixes

- _(cli)_ Keep Fish completion candidates whole and on one line
- _(agent)_ Name date-filter time bases and reject zero-length windows
- _(secret)_ Supply scoped credentials without reading dot.yaml
- _(trust)_ Report when no harness has state to trust

### ♻️ Refactor

- _(process)_ Classify probe timeouts by error type
- _(tasks)_ Drop an unused release helper and a redundant audit guard

### 📚 Documentation

- _(dot-cli)_ Document scoped secrets, trust notices, cache labels, and date rules
- Illustrate the README and add an SVG illustration standard

### 🧪 Testing

- _(agy)_ Keep the registry sentinel out of macOS temporary paths
- _(clipboard)_ Pin the Sommelier signal in backend selection cases

### ⚙️ Build & CI

- Drop redundant ignore patterns and widen format and lint coverage
- _(tools)_ Drop harper-ls and its Neovim prose LSP

### 🧹 Miscellaneous

- _(deps)_ Refresh locked tools and sidecar dependency graphs

## [8.3.0] - 2026-10-04

### 🚀 Features

- _(theme)_ Fetch the lazygit theme and guard copied theme blocks
- _(shell)_ End-mark managed shell blocks and migrate legacy ones

### ♻️ Refactor

- _(config)_ Retire completed host migrations and bridges
- _(skills)_ Replace the lexical routing fixture with package and budget checks
- _(dot)_ Simplify CLI internals and the release task

### 📚 Documentation

- _(agy)_ Document agy 1.2.16 modes, remote control, and SDK usage

### 🧪 Testing

- _(process)_ Let the SIGTERM timeout case outlast loaded interpreter startup

## [8.2.0] - 2026-10-03

### 🚀 Features

- _(agents)_ Replace verifier with security-reviewer
- _(agents)_ Expand shared roles and rename reviewer to code-reviewer
- _(skills)_ Add clipboard skill
- _(agy)_ Add structured review, project sync, and status display
- _(dot)_ Add doctor --headroom and concise agent context checks

### 🐛 Bug Fixes

- _(tasks)_ Target the dot project explicitly in uv tasks

### 📚 Documentation

- _(skills)_ Ship Zensical starter templates for documentation sites

### 🧪 Testing

- _(agy)_ Cover review task, project sync, and status display

### ⚙️ Build & CI

- _(tools)_ Add ffmpeg, harper-ls, and typos; drop kube-linter

## [8.1.3] - 2026-10-03

### 📚 Documentation

- _(skills)_ Align bf-use with Brain Framework 18.1.1

### 🧹 Miscellaneous

- _(deps)_ Lock Brain Framework 18.1.1

## [8.1.2] - 2026-10-03

### 📚 Documentation

- _(skills)_ Align bf-use with Brain Framework 18.1.0

### 🧹 Miscellaneous

- _(deps)_ Lock Brain Framework 18.1.0

## [8.1.1] - 2026-10-03

### 🐛 Bug Fixes

- _(mise)_ Serialize Trivy tasks that share the vulnerability database

## [8.1.0] - 2026-10-03

### 🚀 Features

- _(theme)_ Pin fmind/theme externals to a checksummed commit

### 🐛 Bug Fixes

- _(skills)_ Pin mise in shipped workflow and mise templates

### ⚙️ Build & CI

- Run starter contracts on Linux

## [8.0.0] - 2026-10-03

### 🚀 Features

- _(cli)_ [**breaking**] Unify JSON envelopes, GitHub host, and short flags

### 🐛 Bug Fixes

- _(chezmoi)_ Refuse to replace host skill directories and end shell blocks with a newline

### 📚 Documentation

- _(skills)_ Give Colab auth and skill registration single owners

### 🧹 Miscellaneous

- Exclude generated locks from ripgrep and fd searches
- _(mise)_ Run the watched test suite once at startup
- _(deps)_ Upgrade tools, tool environments, and Neovim plugins

## [7.13.0] - 2026-10-03

### 🚀 Features

- _(auth)_ Add `dot login colab` with required ADC scopes and verified session access

### 📚 Documentation

- _(skills)_ Align bf-use with Brain Framework 18

### 🧹 Miscellaneous

- _(deps)_ Lock Brain Framework 18.0.0

## [7.12.0] - 2026-10-02

### 🚀 Features

- _(mise)_ Add sonarqube-cli to workstation tools (#97)
- _(mise)_ Add cloudflare cf cli (#98)
- _(nvim)_ Add <leader>fh keymap to show and copy full file path (#99)
- _(mise)_ Adopt lockfile revision 3 and refresh the tool baseline
- _(agents)_ Disable claude.ai skill sync and tighten harness settings
- _(agy)_ Prune stale Remote Control registry entries

### 🐛 Bug Fixes

- _(fish)_ Return to the shell when Zellij exits
- _(trust)_ Note inherited Copilot trust for skipped repositories
- _(dot)_ Correct usage accounting and harden session archiving
- _(chezmoi)_ Skip keyless bf credentials and survive Crostini OOM kills
- _(security)_ Require mise 2026.10.0 and tighten scans, CI, and defaults
- _(config)_ Correct Atuin, Ghostty, Neovim, and app defaults
- _(gws)_ Keep smart-chip text in document exports
- _(skills)_ Accept max effort in deleguate-tasks

### 📚 Documentation

- _(kaggle)_ Schedule competition deadline reminders
- Synchronize skills and README with dot behavior
- _(skills)_ Align bf-use with Brain Framework 17
- _(skills)_ Align skills with current tools and repository practice

### 🧪 Testing

- Keep usage-error and submodule tests independent of CI color and Git identity

### 🧹 Miscellaneous

- _(deps)_ Upgrade tools and Neovim plugins
- _(deps)_ Lock Brain Framework 16.1.1 and Claude Code 2.1.285
- _(deps)_ Bump the actions group across 2 directories with 3 updates (#96)
- _(deps)_ Lock Brain Framework 17.0.0

## [7.11.0] - 2026-09-29

### 🚀 Features

- _(workspace)_ Add reactions, media, activity, support, and profile scopes

### 📚 Documentation

- _(skills)_ Align bf-use with Brain Framework 16.1

### 🧹 Miscellaneous

- _(deps)_ Lock Brain Framework 16.1.0

## [7.10.0] - 2026-09-29

### 🚀 Features

- _(agent)_ Notify on idle turns and use native harness attention
- Add .ignore template and project search guidelines

### 📚 Documentation

- _(skills)_ Align bf-use with Brain Framework 15
- _(skills)_ Align bf-use with Brain Framework 16

### 🧪 Testing

- Isolate tests from the repository Git exports to hooks

### 🧹 Miscellaneous

- _(deps)_ Lock Brain Framework 15.0.0
- _(deps)_ Upgrade workstation tools, dependencies, and plugins
- _(deps)_ Lock Brain Framework 16.0.1

## [7.9.1] - 2026-09-28

### 🐛 Bug Fixes

- Keep the Brain Framework config directory private

### 📚 Documentation

- _(skills)_ Align bf-use with Brain Framework 14
- _(skills)_ Correct bf-use execution, schedule and attention rules

### 🧹 Miscellaneous

- _(deps)_ Update Brain Framework to 14.0.0

## [7.9.0] - 2026-09-27

### 🚀 Features

- Integrate shared agents and preserve complete archive usage
- Adopt strict Supagents 1.4 verification

### 🐛 Bug Fixes

- Prevent bytecode races during chezmoi checks

### ⚙️ Build & CI

- Adopt supagents 1.3.0 from PyPI

## [7.8.0] - 2026-09-26

### 🚀 Features

- _(secrets)_ Add OpenRouter management key for usage reporting

### 🐛 Bug Fixes

- Harden CLI accounting, tooling, and operational guidance

### 🧪 Testing

- Resolve mise configuration paths on macOS

### 🧹 Miscellaneous

- _(agents)_ Update Brain Framework to 12.0.0 and its bf-use guidance
- _(deps)_ Update Brain Framework to 12.0.2

## [7.7.1] - 2026-09-25

### 🐛 Bug Fixes

- Harden lockfile recovery and workstation upgrades

### 📚 Documentation

- _(skills)_ Mirror Brain Framework 11 guidance in bf-use

### 🧹 Miscellaneous

- _(deps)_ Upgrade Brain Framework to 11.0.0

## [7.7.0] - 2026-09-25

### 🚀 Features

- _(workstation)_ Integrate Brain Framework
- _(nvim)_ Enhance buffer deletion, snacks pickers, and formatting

### 🐛 Bug Fixes

- Harden test runner, macos locks, starters, and tool audit (#94)
- Qualify macOS runtime and audit configured tool versions

### 📚 Documentation

- _(skills)_ Mirror Brain Framework guidance in bf-use
- _(skills)_ Mirror the Brain Framework assets folder guidance
- _(skills)_ Fix lefthook staged leaks task reference

### 🧹 Miscellaneous

- _(deps)_ Upgrade Brain Framework to 9.1.0
- _(deps)_ Upgrade Brain Framework to 9.2.0

## [7.6.0] - 2026-09-24

### 🚀 Features

- _(workstation)_ Support local configs, dynamic claude env, and bitwarden/vault tools (#93)

### 🧹 Miscellaneous

- _(deps)_ Upgrade FKF to 8.2.2
- _(workstation)_ Merge remote config support with FKF upgrade
- _(workstation)_ Remove FKF integration

## [7.5.0] - 2026-09-24

### 🚀 Features

- _(skills)_ Add dot-verify and run it before every dot-release

## [7.4.0] - 2026-09-24

### 🚀 Features

- _(dot)_ Add dot orphan and report retained sessions in agent doctor

### 🧹 Miscellaneous

- _(deps)_ Upgrade FKF to 8.2.1
- _(deps)_ Upgrade workstation tools, drop the Colab kernel pin, and keep acli completions
- _(pricing)_ Refresh API prices and add missing GPT-5 and dated Claude models

## [7.3.0] - 2026-09-23

### 🚀 Features

- Lock tool dependency graphs and harden archives, hooks, and trust

### 🧹 Miscellaneous

- _(mise)_ Lock fkf 8.0.1
- _(fkf)_ Lock fkf 8.1.0 and sync the learning guide
- _(mise)_ Update fmind CLI to 2.0.1

## [7.2.0] - 2026-09-23

### 🚀 Features

- _(fkf)_ Declare FKF 8 bases, hourly updates and the knowledge skill

### 🧹 Miscellaneous

- _(mise)_ Lock fkf 8.0.0

## [7.1.0] - 2026-09-22

### 🚀 Features

- _(bootstrap)_ Defer hooks until tools install and add full task
- _(security)_ Narrow workspace trust and harden release, deploy, and hooks

## [7.0.4] - 2026-09-21

### 📚 Documentation

- _(security)_ Add audit coverage records and AI boundary checks

## [7.0.3] - 2026-09-20

### 🐛 Bug Fixes

- _(release)_ Include dependency upgrades in patch releases

### 🧹 Miscellaneous

- _(deps)_ Upgrade workstation tools and Neovim plugins

## [7.0.2] - 2026-09-20

### 🐛 Bug Fixes

- Harden session archives and streamline workstation workflows

## [7.0.1] - 2026-09-19

### 🐛 Bug Fixes

- _(release)_ Resolve publication notes from the repository root

## [7.0.0] - 2026-09-19

### 🚀 Features

- _(dot)_ Add fish completions for extra mise tools (#91)
- _(mise)_ Merge optional tool extras into workstation baseline (#92)
- _(workstation)_ Refresh tool defaults, retire cursor and terraform
- _(dot)_ Add dot trust to pre-accept harness folder trust
- _(workstation)_ Trust mise configs under home and approve brain MCP
- _(agent)_ [**breaking**] Keep the latest copy per session and capture by incremental sync
- _(harness)_ Keep only notify hooks and clear retired capture events
- _(secrets)_ Replace shell exports with scoped credentials

### 🐛 Bug Fixes

- _(workstation)_ Rebuild the bat theme cache in the same apply
- _(workstation)_ Restore zellij normal mode by default
- _(dot)_ Keep Ctrl+C responsive at the prune confirmation
- _(archive)_ Keep the last measured usage when extraction fails
- _(auth)_ Treat expired gcloud sessions as needing login
- _(release)_ Accept only plain release version tags
- _(archive)_ Serialize publication and keep sync previews read-only
- _(docs)_ Correct credential imports before release

### ♻️ Refactor

- _(dot)_ Harden archive, process, and release tasks
- _(skills)_ Merge planning and script guides, drop cursor and jules

### 📚 Documentation

- Sync README and AGENTS with the workstation changes
- Fix stale CLI migration, notification, and uninstall notes
- _(dot)_ Document the v3 session store, sync-only capture, and agent doctor checks

### ⚙️ Build & CI

- Split local and network checks and stage release publishing

### 🧹 Miscellaneous

- _(deps)_ Update Tree-sitter plugin

## [6.3.2] - 2026-09-18

### 🐛 Bug Fixes

- _(workstation)_ Include pending health and configuration fixes

## [6.3.1] - 2026-09-17

### 🐛 Bug Fixes

- _(agent)_ Restore hooks and improve desktop notifications

## [6.3.0] - 2026-09-17

### 🚀 Features

- _(mise)_ Modularize tool extras and add cloud, data, and cluster skills (#90)
- Add model-providers skill and configure openrouter for opencode

### 🐛 Bug Fixes

- _(mise)_ Bundle pgcli PostgreSQL client libraries

## [6.2.1] - 2026-09-16

### 🐛 Bug Fixes

- _(test)_ Normalize colored context validation errors

## [6.2.0] - 2026-09-16

### 🚀 Features

- _(skills)_ Consolidate catalog and secure upgrades

## [6.1.0] - 2026-09-16

### 🚀 Features

- _(agy)_ Update completions, features reference, and task tests
- _(skills)_ Add copier skill and template defaults
- _(skills)_ Enrich task delegation outputs and update tracking docs

### 🐛 Bug Fixes

- _(test)_ Strip ansi escapes and add delegation batch script

### 📚 Documentation

- _(skills)_ Refine cli contracts and delegation tracking guidelines

### 🧪 Testing

- _(skills)_ Test native agy defaults and typecheck script

## [6.0.1] - 2026-09-16

### 🐛 Bug Fixes

- _(test)_ Neutralize runner color in session window CLI test

## [6.0.0] - 2026-09-16

### 🚀 Features

- _(cli)_ [**breaking**] Consolidate agent stats and modernize cli contracts
- _(skills)_ Add deleguate-tasks skill

## [5.2.0] - 2026-09-15

### 🚀 Features

- _(skills)_ Add terms-review and agy repository indexing

## [5.1.1] - 2026-09-15

### 🐛 Bug Fixes

- _(cli)_ Keep prune confirmation responsive to interrupts

## [5.1.0] - 2026-09-15

### 🚀 Features

- Add a2a CLI and link upstream releases across skills
- _(theme)_ Wire fmind/theme v2.1.0 across every themed tool
- _(theme)_ Wire lualine and bump fmind/theme to v2.2.0
- Adopt light theme, Google Sans fonts, and new skills
- _(mise)_ Establish shared tool baseline and prune unused tools
- _(workstation)_ Refine fonts, notifications, and tool defaults

### 🐛 Bug Fixes

- _(theme)_ Follow upstream main and refresh externals on apply
- Harden archive cleanup and terminal cancellation tests

### 📚 Documentation

- _(skills)_ Update langchain and langgraph for v1 APIs
- _(skills)_ Document resource budgets and refresh references

### 🧪 Testing

- Give the harness renderer the theme_variant it now needs

### 🧹 Miscellaneous

- _(deps)_ Upgrade toolchain and dependency locks

## [5.0.2] - 2026-09-11

### 🐛 Bug Fixes

- _(dot)_ Drop GITHUB_ACTIONS from the starter contract environment

## [5.0.1] - 2026-09-11

### 🐛 Bug Fixes

- _(dot)_ Keep starter contracts color-free so CD assertions hold

## [5.0.0] - 2026-09-11

### 🚀 Features

- [**breaking**] Overhaul the Python experience and consolidate the skill catalog

### 🐛 Bug Fixes

- _(cursor)_ Install cursor-agent via bootstrap hook instead of mise (#88)
- Document every --json flag and align managed defaults

## [4.1.0] - 2026-09-10

### 🚀 Features

- Expand agent skills and modularize mise tasks

## [4.0.0] - 2026-09-10

### 🐛 Bug Fixes

- _(dot)_ Version statistics schemas after removing legacy counters

### ♻️ Refactor

- _(dot)_ [**breaking**] Remove legacy formats and start a fresh archive

## [3.0.1] - 2026-09-10

### 🐛 Bug Fixes

- _(ci)_ Make signal and shell contracts portable across runners
- _(cloud-run)_ Reject invalid inputs without relying on errexit

## [3.0.0] - 2026-09-10

### 🚀 Features

- Expand agent harnesses and skill catalog
- _(dot)_ [**breaking**] Simplify runtime and unify transactional session archives

### 🐛 Bug Fixes

- _(dot)_ Open browser on workspace login and drop keep scope (#85)
- _(dot)_ Fix d2 backend and make tool completions non-blocking (#86)
- _(opencode)_ Restore template delimiters in modify_opencode.json (#87)

### 🧹 Miscellaneous

- Merge upstream OpenCode template repair

## [2.1.0] - 2026-09-09

### 🚀 Features

- Add opencode agent harness and marimo support

## [2.0.1] - 2026-09-08

### 🐛 Bug Fixes

- _(deploy)_ Verify installed CLI via version option

## [2.0.0] - 2026-09-08

### 🐛 Bug Fixes

- _(test)_ Resolve darwin parity and deploy script errexit validation (#84)

### ♻️ Refactor

- [**breaking**] Simplify dot CLI and agent workflows

## [1.27.0] - 2026-09-06

### 🚀 Features

- _(dot)_ Migrate CLI from Go to Python

### 🐛 Bug Fixes

- Harden tooling, agent workflows, and validation contracts
- _(ci)_ Make Python gate environment-independent

### ♻️ Refactor

- Streamline scripts, agent skill catalog, and tool configs

## [1.26.2] - 2026-09-04

### 📚 Documentation

- _(mermaid)_ Require clear human-readable labels in diagram standard

## [1.26.1] - 2026-09-04

### 🐛 Bug Fixes

- Upgrade tools and handle darwin symlinks in prune validation (#82)

### 🧹 Miscellaneous

- _(mise)_ Update tool and neovim plugin lockfiles

## [1.26.0] - 2026-09-04

### 🚀 Features

- _(skills)_ Update global skills and tooling contracts
- _(dot)_ Add agent usage tracking and expand skills catalog

## [1.25.1] - 2026-08-30

### 🐛 Bug Fixes

- _(mise)_ Use musl assets for atuin and update tool locks

## [1.25.0] - 2026-08-30

### 🚀 Features

- _(skills)_ Expand workflows and release verification

## [1.24.0] - 2026-08-29

### 🚀 Features

- _(mise)_ Add fgraph tool

## [1.23.0] - 2026-08-27

### 🚀 Features

- _(config)_ Update lazygit, copilot, and fish environment (#80)
- _(secrets)_ Add UV_PUBLISH_TOKEN for package publishing

## [1.22.1] - 2026-08-23

### 🐛 Bug Fixes

- _(dot)_ Drop keep scope and extend session retention

## [1.22.0] - 2026-08-23

### 🚀 Features

- _(mise)_ Add acli tool and update lockfiles
- _(dot)_ Add contacts.other and keep scopes to default workspace login

## [1.21.0] - 2026-08-22

### 🚀 Features

- _(skills)_ Add full-review skill for repo health audits

### 🐛 Bug Fixes

- _(grok)_ Require the exact install path for the bootstrap idempotency check
- _(agent)_ Prune Grok's chat_history.jsonl sibling with its transcript
- _(skills)_ Correct stale version pins and a renamed task reference

### 🧹 Miscellaneous

- _(deps)_ Upgrade mise tools, Go modules, and formatter plugins

## [1.20.0] - 2026-08-21

### 🚀 Features

- _(grok)_ Enable native auto-update and bootstrap hook (#79)
- _(nvim)_ Enable inline buffer image previews in snacks.nvim

## [1.19.0] - 2026-08-16

### 🚀 Features

- _(grok)_ Enable vim editing in the prompt

## [1.18.3] - 2026-08-16

### 📚 Documentation

- _(fish)_ Drop the GROK_WEB_FETCH rationale comment

### 🧹 Miscellaneous

- _(deps)_ Bump mason-lspconfig.nvim

## [1.18.2] - 2026-08-16

### 🐛 Bug Fixes

- _(grok)_ Correct the lock note now that mise checksums grok

### 🧹 Miscellaneous

- _(deps)_ Upgrade mise toolchain and Neovim plugins

## [1.18.1] - 2026-08-16

### 🐛 Bug Fixes

- _(chezmoi)_ Prune stale agent config keys and pin compat sessions

## [1.18.0] - 2026-08-16

### 🚀 Features

- _(grok)_ Integrate Grok Build CLI as a first-class agent

## [1.17.1] - 2026-08-14

### 🐛 Bug Fixes

- _(mise)_ Use asdf backend for ollama on macOS (#76)

### 🧹 Miscellaneous

- _(deps)_ Update stack templates, skills, and tool pins
- _(deps)_ Update lockfiles and bump default antigravity model

## [1.17.0] - 2026-08-11

### 🚀 Features

- _(skills)_ Add handover skill and GOTH asset bundling

## [1.16.0] - 2026-08-10

### 🚀 Features

- _(dot)_ Add 1-letter path aliases for agent and query commands

## [1.15.2] - 2026-08-10

### ♻️ Refactor

- _(dot)_ Remove externals pull dirs and update agent clean prefixes

## [1.15.1] - 2026-08-10

### 🧹 Miscellaneous

- _(mise)_ Remove ollama

## [1.15.0] - 2026-08-09

### 🚀 Features

- _(dot,nvim)_ Add completion tools and fix likec4 loading

## [1.14.1] - 2026-08-09

### 🐛 Bug Fixes

- _(k3d)_ Remove custom eviction hard kubelet argument

## [1.14.0] - 2026-08-09

### 🚀 Features

- _(skills)_ Merge the product lifecycle into product-loop and rename code-review to diff-review

### 🐛 Bug Fixes

- _(dot)_ Stop verify from reporting healthy tools as broken
- _(k8s-local)_ Move ingress off 8080/8443 and stop DiskPressure from blocking scheduling

## [1.13.1] - 2026-08-08

### 🐛 Bug Fixes

- _(dot)_ Compare evaluated paths in the skill resource containment check

## [1.13.0] - 2026-08-08

### 🚀 Features

- _(skills)_ Add twenty skills and tighten the repository gate

## [1.12.1] - 2026-08-07

### 🐛 Bug Fixes

- _(dot)_ Remove just from completions

## [1.12.0] - 2026-08-07

### 🚀 Features

- _(skills)_ Add skills for cloud-run, hugo, sops-secrets, terraform-stack, and typst

## [1.11.1] - 2026-08-07

### 📚 Documentation

- _(agents)_ Update global instructions and chezmoiignore

## [1.11.0] - 2026-08-06

### 🚀 Features

- _(tools)_ Add slack-cli

## [1.10.7] - 2026-08-04

### 🐛 Bug Fixes

- _(chezmoi)_ Drop leading slashes rejected by chezmoi 2.72
- _(mise)_ Authenticate GitHub API with the gh CLI token

### 🧹 Miscellaneous

- _(mise)_ Build in the all gate and refresh lockfiles
- _(nvim)_ Refresh LazyVim plugin lockfile

## [1.10.6] - 2026-08-04

### 🐛 Bug Fixes

- _(mise)_ Align task execution directories and binary paths (#74)
- _(mise)_ Pin task directories to config_root instead of cwd

## [1.10.5] - 2026-08-02

### 📚 Documentation

- _(agents)_ Require language identifier for markdown code blocks

## [1.10.4] - 2026-08-02

### 🐛 Bug Fixes

- _(claude)_ Update model identifier to opus[1m]

## [1.10.3] - 2026-08-02

### ♻️ Refactor

- _(skills)_ Align skill declarations and update contract tests

## [1.10.2] - 2026-08-02

### ♻️ Refactor

- _(release)_ Simplify release tag workflow and reapply dot binary

## [1.10.1] - 2026-08-02

### 🐛 Bug Fixes

- _(dot)_ Increase default capability probe timeout to 15s

## [1.10.0] - 2026-08-02

### 🚀 Features

- _(verify)_ Gate install freshness on build inputs and redeploy post-commit

### 🐛 Bug Fixes

- _(cluster)_ Create the local cluster when no k3d cluster exists

### 🧹 Miscellaneous

- _(upgrade)_ Bump global tools and Neovim plugins

## [1.9.0] - 2026-08-02

### 🚀 Features

- _(github)_ Add agent-runnable issue queue
- _(release)_ Gate publication on exact-head CI
- _(dot)_ Emit bounded and redacted project context
- _(agent)_ Add cross-agent discovery and hook doctor
- _(cluster)_ Collect bounded sanitized diagnostics
- _(security)_ Add scheduled full-history scans
- _(stacks)_ Resolve exact local dependency source
- _(skill)_ Add exact-head release audit
- _(skill)_ Add cross-cutting repository review
- _(agent)_ Add versioned session query exports
- _(agent)_ Sync Copilot sessions from personal hook (#69)
- _(skill)_ Add evidence-first project backlog (#70)
- _(skill)_ Add bounded Kubernetes review (#71)
- _(skill)_ Add cooperative issue execution (#72)
- _(config)_ Update root directories for fmind, fmind-ai, and mlops-courses
- _(dot)_ Unify agent sources, add configurable bounds, simplify bootstrap

### 🐛 Bug Fixes

- _(verify)_ Probe CLI capabilities instead of shims
- _(ai)_ Pack diffs with explicit omission evidence
- _(agent)_ Make session ingestion lineage-safe
- _(prune)_ Retain raw sessions until verified
- _(cluster)_ Isolate and verify kubeconfig targets
- _(bootstrap)_ Verify pinned installers
- _(bootstrap)_ Trust nested mise configs hermetically
- _(verify)_ Support Helm 4 capability probe (#73)

### ♻️ Refactor

- _(mise)_ Separate update and convergence phases

### 🧪 Testing

- _(docs)_ Validate agent command contracts
- _(ci)_ Validate workflows and skill contracts

## [1.8.0] - 2026-07-31

### 🚀 Features

- _(dot)_ Consolidate prune command into dot cli and refine skills

## [1.7.3] - 2026-07-31

### 🐛 Bug Fixes

- _(skills)_ Correct inaccurate commands and broken hook ordering

### 🧹 Miscellaneous

- _(prune)_ Include the antigravity brain dir in agent transcript pruning

## [1.7.2] - 2026-07-31

### 🐛 Bug Fixes

- _(claude)_ Keep Claude Code runtime settings across chezmoi applies

### 🧪 Testing

- _(dot)_ Expand unit test coverage across dot cli subcommands

## [1.7.1] - 2026-07-31

### ♻️ Refactor

- _(dot)_ Drop the duplicate agent notify subcommand

### 🧹 Miscellaneous

- _(mise)_ Re-sync the global lockfile with installed platforms

## [1.7.0] - 2026-07-31

### 🚀 Features

- _(dot)_ Notify desktop on agent stop and session end

### 🐛 Bug Fixes

- _(ci)_ Lock trivy and restore a green cross-platform pipeline
- _(check)_ Render chezmoi against a seeded config so CI can validate it
- _(dot)_ Stub the platform browser opener so macOS tests pass

### ♻️ Refactor

- _(dot)_ Resolve command alias collisions

## [1.6.0] - 2026-07-31

### 🚀 Features

- Update dot CLI agent tools, dotfiles tasks, and skills

### 🧹 Miscellaneous

- _(claude)_ Remove DISABLE_TELEMETRY setting

## [1.5.0] - 2026-07-16

### 🚀 Features

- _(skills)_ Add visual and presentation skills

## [1.4.4] - 2026-07-15

### 🧹 Miscellaneous

- _(mise)_ Update lockfile

## [1.4.3] - 2026-07-15

### 🧹 Miscellaneous

- Ignore local skills, remove completions hook, update k8s docs

## [1.4.2] - 2026-07-14

### 🧹 Miscellaneous

- _(gh)_ Remove prefer_editor_prompt

## [1.4.1] - 2026-07-14

### 📚 Documentation

- _(agents)_ Allow direct push to main branch

## [1.4.0] - 2026-07-14

### 🚀 Features

- _(bash)_ Add mise activation and paths

## [1.3.0] - 2026-07-14

### 🚀 Features

- _(skills)_ Add dependabot skill

## [1.2.4] - 2026-07-13

### 🧹 Miscellaneous

- Configure lsd and disable slsa attestations in mise

## [1.2.3] - 2026-07-13

### ♻️ Refactor

- Replace eza with lsd

## [1.2.2] - 2026-07-12

### 🐛 Bug Fixes

- _(mise)_ Pin gws to 0.22.4 for glibc compatibility

## [1.2.1] - 2026-07-12

### 🧹 Miscellaneous

- Add hadolint linter and migrate lazygit config

## [1.2.0] - 2026-07-12

### 🚀 Features

- _(dot)_ Add agent session log management command
- _(dot)_ Improve CLI commands, tests, and configuration files

### ♻️ Refactor

- _(dot)_ Consolidate gcloud login and add python-script skill

## [1.1.1] - 2026-07-08

### ♻️ Refactor

- Trim cliff.toml defaults and dot-release skill

## [1.1.0] - 2026-07-08

### 🚀 Features

- _(dot)_ Add release command and html-slides skill

## [1.0.0] - 2026-07-06

### 🚀 Features

- Initial public release
