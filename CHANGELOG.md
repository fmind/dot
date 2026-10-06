# Changelog

All notable changes to this project are documented in this file.
## [10.1.2] - 2026-10-06

### ♻️ Refactor

- *(skills)* Fold containerize into docker and update-ignores into repository-maintenance
- *(agents)* Keep four shared roles in exact agent directories
- *(deploy)* Install the dot CLI with uv tool install

### 📚 Documentation

- *(skills)* Keep image pins in project locks and drop the dot command table
- Trim the persona, project rules, and redundant README illustrations
- *(skills)* Mirror the bf-action skill of Brain Framework 18.2.0

### 🧪 Testing

- Deflake the chezmoi fixture and archive lock race

### 🧹 Miscellaneous

- *(shell)* Simplify editor, pager, ignore, and database preset config
- *(deps)* Upgrade typer, workstation tools, and Neovim plugins
- *(deps)* Lock Brain Framework 18.2.0
## [10.1.1] - 2026-10-06

### 🐛 Bug Fixes

- Support custom meminfo on darwin and deflake agy test timeout
- *(security)* Keep SSH, gws, and cloud credentials out of searches
- *(agy)* Merge user hooks and reload systemd drop-ins on change
- *(config)* Ignore .DS_Store globally and let gh use nvim-tty
- *(hooks)* Format the editor wrapper on commit
- *(delegate-tasks)* Keep the canceled state when a worker ignores SIGTERM
- *(dot)* Name the move-aside step for unreadable transcripts
- *(skills)* Name missing guide markers instead of a no-op fix
- *(skills)* Correct stale commands, policies, and template defaults

### 📚 Documentation

- *(skills)* Trim duplicated archive and pin guidance

### 🧪 Testing

- Deflake timing-bound tests and drop dead fixtures

### 🧹 Miscellaneous

- *(deps)* Upgrade usage, a neovim plugin, and template pins
## [10.1.0] - 2026-10-06

### 🚀 Features

- Add cache/trust JSON, doctor discovery, and agent shell defaults
- *(doctor)* Report caller-environment checks as non-failing notes
- Fail fast instead of opening nvim without a terminal

### 🧹 Miscellaneous

- Drop release-age cooldowns from npm, Dependabot, and skills
- *(deps)* Upgrade tools, theme pin, and editor plugins
## [10.0.0] - 2026-10-05

### ♻️ Refactor

- [**breaking**] Trim unused commands, release publishing, and gates
- Lead rules with bold summaries and open subagent roles
## [9.0.3] - 2026-10-04

### 🐛 Bug Fixes

- *(auth)* Copy the GitHub device code through X11 on Crostini
- *(codex)* Leave a converged config in the layout Codex wrote
## [9.0.2] - 2026-10-04

### 🐛 Bug Fixes

- *(skills)* Publish the Python starter through Trusted Publishing only

### 🧹 Miscellaneous

- *(config)* Retire removal markers that every workstation applied
- *(secrets)* Retire the unused JULES_API_KEY seed
## [9.0.1] - 2026-10-04

### 🐛 Bug Fixes

- *(git)* Match the chezmoi source include through symlinked paths
## [9.0.0] - 2026-10-04

### 🚀 Features

- *(secrets)* [**breaking**] Retire dot secret publish and the personal PyPI token
- *(auth)* Own brain-sensor Workspace scopes and flag plaintext gh tokens
- *(git)* Commit personal checkouts with the personal email
- *(agents)* Register the brain SessionStart hook for Claude and Codex
- *(archive)* Resolve agy workspaces, follow archived Codex rollouts, and prove current transcripts

### 🐛 Bug Fixes

- *(cli)* Report Cancelled. on interrupted commands and drop dead Copilot doctor branches
- *(fish)* Export the fzf theme only once chezmoi fetched it

### 📚 Documentation

- *(skills)* Correct stale commands, links, and tool contracts

### 🧪 Testing

- *(release)* Keep release wait tests with the release suite

### ⚙️ Build & CI

- *(cd)* Gate releases on macOS tests and outlast the publish bounds
- *(mise)* Require mise 2026.10.2 and lock template formatters
## [8.4.0] - 2026-10-04

### 🚀 Features

- *(cache)* Label each provider in a multi-provider report
- *(agent)* Fail context checks on duplicate skill names
- *(skills)* Optimize the catalog and give colliding skills unique names

### 🐛 Bug Fixes

- *(cli)* Keep Fish completion candidates whole and on one line
- *(agent)* Name date-filter time bases and reject zero-length windows
- *(secret)* Supply scoped credentials without reading dot.yaml
- *(trust)* Report when no harness has state to trust

### ♻️ Refactor

- *(process)* Classify probe timeouts by error type
- *(tasks)* Drop an unused release helper and a redundant audit guard

### 📚 Documentation

- *(dot-cli)* Document scoped secrets, trust notices, cache labels, and date rules
- Illustrate the README and add an SVG illustration standard

### 🧪 Testing

- *(agy)* Keep the registry sentinel out of macOS temporary paths
- *(clipboard)* Pin the Sommelier signal in backend selection cases

### ⚙️ Build & CI

- Drop redundant ignore patterns and widen format and lint coverage
- *(tools)* Drop harper-ls and its Neovim prose LSP

### 🧹 Miscellaneous

- *(deps)* Refresh locked tools and sidecar dependency graphs
## [8.3.0] - 2026-10-04

### 🚀 Features

- *(theme)* Fetch the lazygit theme and guard copied theme blocks
- *(shell)* End-mark managed shell blocks and migrate legacy ones

### ♻️ Refactor

- *(config)* Retire completed host migrations and bridges
- *(skills)* Replace the lexical routing fixture with package and budget checks
- *(dot)* Simplify CLI internals and the release task

### 📚 Documentation

- *(agy)* Document agy 1.2.16 modes, remote control, and SDK usage

### 🧪 Testing

- *(process)* Let the SIGTERM timeout case outlast loaded interpreter startup
## [8.2.0] - 2026-10-03

### 🚀 Features

- *(agents)* Replace verifier with security-reviewer
- *(agents)* Expand shared roles and rename reviewer to code-reviewer
- *(skills)* Add clipboard skill
- *(agy)* Add structured review, project sync, and status display
- *(dot)* Add doctor --headroom and concise agent context checks

### 🐛 Bug Fixes

- *(tasks)* Target the dot project explicitly in uv tasks

### 📚 Documentation

- *(skills)* Ship Zensical starter templates for documentation sites

### 🧪 Testing

- *(agy)* Cover review task, project sync, and status display

### ⚙️ Build & CI

- *(tools)* Add ffmpeg, harper-ls, and typos; drop kube-linter
## [8.1.3] - 2026-10-03

### 📚 Documentation

- *(skills)* Align bf-use with Brain Framework 18.1.1

### 🧹 Miscellaneous

- *(deps)* Lock Brain Framework 18.1.1
## [8.1.2] - 2026-10-03

### 📚 Documentation

- *(skills)* Align bf-use with Brain Framework 18.1.0

### 🧹 Miscellaneous

- *(deps)* Lock Brain Framework 18.1.0
## [8.1.1] - 2026-10-03

### 🐛 Bug Fixes

- *(mise)* Serialize Trivy tasks that share the vulnerability database
## [8.1.0] - 2026-10-03

### 🚀 Features

- *(theme)* Pin fmind/theme externals to a checksummed commit

### 🐛 Bug Fixes

- *(skills)* Pin mise in shipped workflow and mise templates

### ⚙️ Build & CI

- Run starter contracts on Linux
## [8.0.0] - 2026-10-03

### 🚀 Features

- *(cli)* [**breaking**] Unify JSON envelopes, GitHub host, and short flags

### 🐛 Bug Fixes

- *(chezmoi)* Refuse to replace host skill directories and end shell blocks with a newline

### 📚 Documentation

- *(skills)* Give Colab auth and skill registration single owners

### 🧹 Miscellaneous

- Exclude generated locks from ripgrep and fd searches
- *(mise)* Run the watched test suite once at startup
- *(deps)* Upgrade tools, tool environments, and Neovim plugins
## [7.13.0] - 2026-10-03

### 🚀 Features

- *(auth)* Add `dot login colab` with required ADC scopes and verified session access

### 📚 Documentation

- *(skills)* Align bf-use with Brain Framework 18

### 🧹 Miscellaneous

- *(deps)* Lock Brain Framework 18.0.0
## [7.12.0] - 2026-10-02

### 🚀 Features

- *(mise)* Add sonarqube-cli to workstation tools (#97)
- *(mise)* Add cloudflare cf cli (#98)
- *(nvim)* Add <leader>fh keymap to show and copy full file path (#99)
- *(mise)* Adopt lockfile revision 3 and refresh the tool baseline
- *(agents)* Disable claude.ai skill sync and tighten harness settings
- *(agy)* Prune stale Remote Control registry entries

### 🐛 Bug Fixes

- *(fish)* Return to the shell when Zellij exits
- *(trust)* Note inherited Copilot trust for skipped repositories
- *(dot)* Correct usage accounting and harden session archiving
- *(chezmoi)* Skip keyless bf credentials and survive Crostini OOM kills
- *(security)* Require mise 2026.10.0 and tighten scans, CI, and defaults
- *(config)* Correct Atuin, Ghostty, Neovim, and app defaults
- *(gws)* Keep smart-chip text in document exports
- *(skills)* Accept max effort in deleguate-tasks

### 📚 Documentation

- *(kaggle)* Schedule competition deadline reminders
- Synchronize skills and README with dot behavior
- *(skills)* Align bf-use with Brain Framework 17
- *(skills)* Align skills with current tools and repository practice

### 🧪 Testing

- Keep usage-error and submodule tests independent of CI color and Git identity

### 🧹 Miscellaneous

- *(deps)* Upgrade tools and Neovim plugins
- *(deps)* Lock Brain Framework 16.1.1 and Claude Code 2.1.285
- *(deps)* Bump the actions group across 2 directories with 3 updates (#96)
- *(deps)* Lock Brain Framework 17.0.0
## [7.11.0] - 2026-09-29

### 🚀 Features

- *(workspace)* Add reactions, media, activity, support, and profile scopes

### 📚 Documentation

- *(skills)* Align bf-use with Brain Framework 16.1

### 🧹 Miscellaneous

- *(deps)* Lock Brain Framework 16.1.0
## [7.10.0] - 2026-09-29

### 🚀 Features

- *(agent)* Notify on idle turns and use native harness attention
- Add .ignore template and project search guidelines

### 📚 Documentation

- *(skills)* Align bf-use with Brain Framework 15
- *(skills)* Align bf-use with Brain Framework 16

### 🧪 Testing

- Isolate tests from the repository Git exports to hooks

### 🧹 Miscellaneous

- *(deps)* Lock Brain Framework 15.0.0
- *(deps)* Upgrade workstation tools, dependencies, and plugins
- *(deps)* Lock Brain Framework 16.0.1
## [7.9.1] - 2026-09-28

### 🐛 Bug Fixes

- Keep the Brain Framework config directory private

### 📚 Documentation

- *(skills)* Align bf-use with Brain Framework 14
- *(skills)* Correct bf-use execution, schedule and attention rules

### 🧹 Miscellaneous

- *(deps)* Update Brain Framework to 14.0.0
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

- *(secrets)* Add OpenRouter management key for usage reporting

### 🐛 Bug Fixes

- Harden CLI accounting, tooling, and operational guidance

### 🧪 Testing

- Resolve mise configuration paths on macOS

### 🧹 Miscellaneous

- *(agents)* Update Brain Framework to 12.0.0 and its bf-use guidance
- *(deps)* Update Brain Framework to 12.0.2
## [7.7.1] - 2026-09-25

### 🐛 Bug Fixes

- Harden lockfile recovery and workstation upgrades

### 📚 Documentation

- *(skills)* Mirror Brain Framework 11 guidance in bf-use

### 🧹 Miscellaneous

- *(deps)* Upgrade Brain Framework to 11.0.0
## [7.7.0] - 2026-09-25

### 🚀 Features

- *(workstation)* Integrate Brain Framework
- *(nvim)* Enhance buffer deletion, snacks pickers, and formatting

### 🐛 Bug Fixes

- Harden test runner, macos locks, starters, and tool audit (#94)
- Qualify macOS runtime and audit configured tool versions

### 📚 Documentation

- *(skills)* Mirror Brain Framework guidance in bf-use
- *(skills)* Mirror the Brain Framework assets folder guidance
- *(skills)* Fix lefthook staged leaks task reference

### 🧹 Miscellaneous

- *(deps)* Upgrade Brain Framework to 9.1.0
- *(deps)* Upgrade Brain Framework to 9.2.0
## [7.6.0] - 2026-09-24

### 🚀 Features

- *(workstation)* Support local configs, dynamic claude env, and bitwarden/vault tools (#93)

### 🧹 Miscellaneous

- *(deps)* Upgrade FKF to 8.2.2
- *(workstation)* Merge remote config support with FKF upgrade
- *(workstation)* Remove FKF integration
## [7.5.0] - 2026-09-24

### 🚀 Features

- *(skills)* Add dot-verify and run it before every dot-release
## [7.4.0] - 2026-09-24

### 🚀 Features

- *(dot)* Add dot orphan and report retained sessions in agent doctor

### 🧹 Miscellaneous

- *(deps)* Upgrade FKF to 8.2.1
- *(deps)* Upgrade workstation tools, drop the Colab kernel pin, and keep acli completions
- *(pricing)* Refresh API prices and add missing GPT-5 and dated Claude models
## [7.3.0] - 2026-09-23

### 🚀 Features

- Lock tool dependency graphs and harden archives, hooks, and trust

### 🧹 Miscellaneous

- *(mise)* Lock fkf 8.0.1
- *(fkf)* Lock fkf 8.1.0 and sync the learning guide
- *(mise)* Update fmind CLI to 2.0.1
## [7.2.0] - 2026-09-23

### 🚀 Features

- *(fkf)* Declare FKF 8 bases, hourly updates and the knowledge skill

### 🧹 Miscellaneous

- *(mise)* Lock fkf 8.0.0
## [7.1.0] - 2026-09-22

### 🚀 Features

- *(bootstrap)* Defer hooks until tools install and add full task
- *(security)* Narrow workspace trust and harden release, deploy, and hooks
## [7.0.4] - 2026-09-21

### 📚 Documentation

- *(security)* Add audit coverage records and AI boundary checks
## [7.0.3] - 2026-09-20

### 🐛 Bug Fixes

- *(release)* Include dependency upgrades in patch releases

### 🧹 Miscellaneous

- *(deps)* Upgrade workstation tools and Neovim plugins
## [7.0.2] - 2026-09-20

### 🐛 Bug Fixes

- Harden session archives and streamline workstation workflows
## [7.0.1] - 2026-09-19

### 🐛 Bug Fixes

- *(release)* Resolve publication notes from the repository root
## [7.0.0] - 2026-09-19

### 🚀 Features

- *(dot)* Add fish completions for extra mise tools (#91)
- *(mise)* Merge optional tool extras into workstation baseline (#92)
- *(workstation)* Refresh tool defaults, retire cursor and terraform
- *(dot)* Add dot trust to pre-accept harness folder trust
- *(workstation)* Trust mise configs under home and approve brain MCP
- *(agent)* [**breaking**] Keep the latest copy per session and capture by incremental sync
- *(harness)* Keep only notify hooks and clear retired capture events
- *(secrets)* Replace shell exports with scoped credentials

### 🐛 Bug Fixes

- *(workstation)* Rebuild the bat theme cache in the same apply
- *(workstation)* Restore zellij normal mode by default
- *(dot)* Keep Ctrl+C responsive at the prune confirmation
- *(archive)* Keep the last measured usage when extraction fails
- *(auth)* Treat expired gcloud sessions as needing login
- *(release)* Accept only plain release version tags
- *(archive)* Serialize publication and keep sync previews read-only
- *(docs)* Correct credential imports before release

### ♻️ Refactor

- *(dot)* Harden archive, process, and release tasks
- *(skills)* Merge planning and script guides, drop cursor and jules

### 📚 Documentation

- Sync README and AGENTS with the workstation changes
- Fix stale CLI migration, notification, and uninstall notes
- *(dot)* Document the v3 session store, sync-only capture, and agent doctor checks

### ⚙️ Build & CI

- Split local and network checks and stage release publishing

### 🧹 Miscellaneous

- *(deps)* Update Tree-sitter plugin
## [6.3.2] - 2026-09-18

### 🐛 Bug Fixes

- *(workstation)* Include pending health and configuration fixes
## [6.3.1] - 2026-09-17

### 🐛 Bug Fixes

- *(agent)* Restore hooks and improve desktop notifications
## [6.3.0] - 2026-09-17

### 🚀 Features

- *(mise)* Modularize tool extras and add cloud, data, and cluster skills (#90)
- Add model-providers skill and configure openrouter for opencode

### 🐛 Bug Fixes

- *(mise)* Bundle pgcli PostgreSQL client libraries
## [6.2.1] - 2026-09-16

### 🐛 Bug Fixes

- *(test)* Normalize colored context validation errors
## [6.2.0] - 2026-09-16

### 🚀 Features

- *(skills)* Consolidate catalog and secure upgrades
## [6.1.0] - 2026-09-16

### 🚀 Features

- *(agy)* Update completions, features reference, and task tests
- *(skills)* Add copier skill and template defaults
- *(skills)* Enrich task delegation outputs and update tracking docs

### 🐛 Bug Fixes

- *(test)* Strip ansi escapes and add delegation batch script

### 📚 Documentation

- *(skills)* Refine cli contracts and delegation tracking guidelines

### 🧪 Testing

- *(skills)* Test native agy defaults and typecheck script
## [6.0.1] - 2026-09-16

### 🐛 Bug Fixes

- *(test)* Neutralize runner color in session window CLI test
## [6.0.0] - 2026-09-16

### 🚀 Features

- *(cli)* [**breaking**] Consolidate agent stats and modernize cli contracts
- *(skills)* Add deleguate-tasks skill
## [5.2.0] - 2026-09-15

### 🚀 Features

- *(skills)* Add terms-review and agy repository indexing
## [5.1.1] - 2026-09-15

### 🐛 Bug Fixes

- *(cli)* Keep prune confirmation responsive to interrupts
## [5.1.0] - 2026-09-15

### 🚀 Features

- Add a2a CLI and link upstream releases across skills
- *(theme)* Wire fmind/theme v2.1.0 across every themed tool
- *(theme)* Wire lualine and bump fmind/theme to v2.2.0
- Adopt light theme, Google Sans fonts, and new skills
- *(mise)* Establish shared tool baseline and prune unused tools
- *(workstation)* Refine fonts, notifications, and tool defaults

### 🐛 Bug Fixes

- *(theme)* Follow upstream main and refresh externals on apply
- Harden archive cleanup and terminal cancellation tests

### 📚 Documentation

- *(skills)* Update langchain and langgraph for v1 APIs
- *(skills)* Document resource budgets and refresh references

### 🧪 Testing

- Give the harness renderer the theme_variant it now needs

### 🧹 Miscellaneous

- *(deps)* Upgrade toolchain and dependency locks
## [5.0.2] - 2026-09-11

### 🐛 Bug Fixes

- *(dot)* Drop GITHUB_ACTIONS from the starter contract environment
## [5.0.1] - 2026-09-11

### 🐛 Bug Fixes

- *(dot)* Keep starter contracts color-free so CD assertions hold
## [5.0.0] - 2026-09-11

### 🚀 Features

- [**breaking**] Overhaul the Python experience and consolidate the skill catalog

### 🐛 Bug Fixes

- *(cursor)* Install cursor-agent via bootstrap hook instead of mise (#88)
- Document every --json flag and align managed defaults
## [4.1.0] - 2026-09-10

### 🚀 Features

- Expand agent skills and modularize mise tasks
## [4.0.0] - 2026-09-10

### 🐛 Bug Fixes

- *(dot)* Version statistics schemas after removing legacy counters

### ♻️ Refactor

- *(dot)* [**breaking**] Remove legacy formats and start a fresh archive
## [3.0.1] - 2026-09-10

### 🐛 Bug Fixes

- *(ci)* Make signal and shell contracts portable across runners
- *(cloud-run)* Reject invalid inputs without relying on errexit
## [3.0.0] - 2026-09-10

### 🚀 Features

- Expand agent harnesses and skill catalog
- *(dot)* [**breaking**] Simplify runtime and unify transactional session archives

### 🐛 Bug Fixes

- *(dot)* Open browser on workspace login and drop keep scope (#85)
- *(dot)* Fix d2 backend and make tool completions non-blocking (#86)
- *(opencode)* Restore template delimiters in modify_opencode.json (#87)

### 🧹 Miscellaneous

- Merge upstream OpenCode template repair
## [2.1.0] - 2026-09-09

### 🚀 Features

- Add opencode agent harness and marimo support
## [2.0.1] - 2026-09-08

### 🐛 Bug Fixes

- *(deploy)* Verify installed CLI via version option
## [2.0.0] - 2026-09-08

### 🐛 Bug Fixes

- *(test)* Resolve darwin parity and deploy script errexit validation (#84)

### ♻️ Refactor

- [**breaking**] Simplify dot CLI and agent workflows
## [1.27.0] - 2026-09-06

### 🚀 Features

- *(dot)* Migrate CLI from Go to Python

### 🐛 Bug Fixes

- Harden tooling, agent workflows, and validation contracts
- *(ci)* Make Python gate environment-independent

### ♻️ Refactor

- Streamline scripts, agent skill catalog, and tool configs
## [1.26.2] - 2026-09-04

### 📚 Documentation

- *(mermaid)* Require clear human-readable labels in diagram standard
## [1.26.1] - 2026-09-04

### 🐛 Bug Fixes

- Upgrade tools and handle darwin symlinks in prune validation (#82)

### 🧹 Miscellaneous

- *(mise)* Update tool and neovim plugin lockfiles
## [1.26.0] - 2026-09-04

### 🚀 Features

- *(skills)* Update global skills and tooling contracts
- *(dot)* Add agent usage tracking and expand skills catalog
## [1.25.1] - 2026-08-30

### 🐛 Bug Fixes

- *(mise)* Use musl assets for atuin and update tool locks
## [1.25.0] - 2026-08-30

### 🚀 Features

- *(skills)* Expand workflows and release verification
## [1.24.0] - 2026-08-29

### 🚀 Features

- *(mise)* Add fgraph tool
## [1.23.0] - 2026-08-27

### 🚀 Features

- *(config)* Update lazygit, copilot, and fish environment (#80)
- *(secrets)* Add UV_PUBLISH_TOKEN for package publishing
## [1.22.1] - 2026-08-23

### 🐛 Bug Fixes

- *(dot)* Drop keep scope and extend session retention
## [1.22.0] - 2026-08-23

### 🚀 Features

- *(mise)* Add acli tool and update lockfiles
- *(dot)* Add contacts.other and keep scopes to default workspace login
## [1.21.0] - 2026-08-22

### 🚀 Features

- *(skills)* Add full-review skill for repo health audits

### 🐛 Bug Fixes

- *(grok)* Require the exact install path for the bootstrap idempotency check
- *(agent)* Prune Grok's chat_history.jsonl sibling with its transcript
- *(skills)* Correct stale version pins and a renamed task reference

### 🧹 Miscellaneous

- *(deps)* Upgrade mise tools, Go modules, and formatter plugins
## [1.20.0] - 2026-08-21

### 🚀 Features

- *(grok)* Enable native auto-update and bootstrap hook (#79)
- *(nvim)* Enable inline buffer image previews in snacks.nvim
## [1.19.0] - 2026-08-16

### 🚀 Features

- *(grok)* Enable vim editing in the prompt
## [1.18.3] - 2026-08-16

### 📚 Documentation

- *(fish)* Drop the GROK_WEB_FETCH rationale comment

### 🧹 Miscellaneous

- *(deps)* Bump mason-lspconfig.nvim
## [1.18.2] - 2026-08-16

### 🐛 Bug Fixes

- *(grok)* Correct the lock note now that mise checksums grok

### 🧹 Miscellaneous

- *(deps)* Upgrade mise toolchain and Neovim plugins
## [1.18.1] - 2026-08-16

### 🐛 Bug Fixes

- *(chezmoi)* Prune stale agent config keys and pin compat sessions
## [1.18.0] - 2026-08-16

### 🚀 Features

- *(grok)* Integrate Grok Build CLI as a first-class agent
## [1.17.1] - 2026-08-14

### 🐛 Bug Fixes

- *(mise)* Use asdf backend for ollama on macOS (#76)

### 🧹 Miscellaneous

- *(deps)* Update stack templates, skills, and tool pins
- *(deps)* Update lockfiles and bump default antigravity model
## [1.17.0] - 2026-08-11

### 🚀 Features

- *(skills)* Add handover skill and GOTH asset bundling
## [1.16.0] - 2026-08-10

### 🚀 Features

- *(dot)* Add 1-letter path aliases for agent and query commands
## [1.15.2] - 2026-08-10

### ♻️ Refactor

- *(dot)* Remove externals pull dirs and update agent clean prefixes
## [1.15.1] - 2026-08-10

### 🧹 Miscellaneous

- *(mise)* Remove ollama
## [1.15.0] - 2026-08-09

### 🚀 Features

- *(dot,nvim)* Add completion tools and fix likec4 loading
## [1.14.1] - 2026-08-09

### 🐛 Bug Fixes

- *(k3d)* Remove custom eviction hard kubelet argument
## [1.14.0] - 2026-08-09

### 🚀 Features

- *(skills)* Merge the product lifecycle into product-loop and rename code-review to diff-review

### 🐛 Bug Fixes

- *(dot)* Stop verify from reporting healthy tools as broken
- *(k8s-local)* Move ingress off 8080/8443 and stop DiskPressure from blocking scheduling
## [1.13.1] - 2026-08-08

### 🐛 Bug Fixes

- *(dot)* Compare evaluated paths in the skill resource containment check
## [1.13.0] - 2026-08-08

### 🚀 Features

- *(skills)* Add twenty skills and tighten the repository gate
## [1.12.1] - 2026-08-07

### 🐛 Bug Fixes

- *(dot)* Remove just from completions
## [1.12.0] - 2026-08-07

### 🚀 Features

- *(skills)* Add skills for cloud-run, hugo, sops-secrets, terraform-stack, and typst
## [1.11.1] - 2026-08-07

### 📚 Documentation

- *(agents)* Update global instructions and chezmoiignore
## [1.11.0] - 2026-08-06

### 🚀 Features

- *(tools)* Add slack-cli
## [1.10.7] - 2026-08-04

### 🐛 Bug Fixes

- *(chezmoi)* Drop leading slashes rejected by chezmoi 2.72
- *(mise)* Authenticate GitHub API with the gh CLI token

### 🧹 Miscellaneous

- *(mise)* Build in the all gate and refresh lockfiles
- *(nvim)* Refresh LazyVim plugin lockfile
## [1.10.6] - 2026-08-04

### 🐛 Bug Fixes

- *(mise)* Align task execution directories and binary paths (#74)
- *(mise)* Pin task directories to config_root instead of cwd
## [1.10.5] - 2026-08-02

### 📚 Documentation

- *(agents)* Require language identifier for markdown code blocks
## [1.10.4] - 2026-08-02

### 🐛 Bug Fixes

- *(claude)* Update model identifier to opus[1m]
## [1.10.3] - 2026-08-02

### ♻️ Refactor

- *(skills)* Align skill declarations and update contract tests
## [1.10.2] - 2026-08-02

### ♻️ Refactor

- *(release)* Simplify release tag workflow and reapply dot binary
## [1.10.1] - 2026-08-02

### 🐛 Bug Fixes

- *(dot)* Increase default capability probe timeout to 15s
## [1.10.0] - 2026-08-02

### 🚀 Features

- *(verify)* Gate install freshness on build inputs and redeploy post-commit

### 🐛 Bug Fixes

- *(cluster)* Create the local cluster when no k3d cluster exists

### 🧹 Miscellaneous

- *(upgrade)* Bump global tools and Neovim plugins
## [1.9.0] - 2026-08-02

### 🚀 Features

- *(github)* Add agent-runnable issue queue
- *(release)* Gate publication on exact-head CI
- *(dot)* Emit bounded and redacted project context
- *(agent)* Add cross-agent discovery and hook doctor
- *(cluster)* Collect bounded sanitized diagnostics
- *(security)* Add scheduled full-history scans
- *(stacks)* Resolve exact local dependency source
- *(skill)* Add exact-head release audit
- *(skill)* Add cross-cutting repository review
- *(agent)* Add versioned session query exports
- *(agent)* Sync Copilot sessions from personal hook (#69)
- *(skill)* Add evidence-first project backlog (#70)
- *(skill)* Add bounded Kubernetes review (#71)
- *(skill)* Add cooperative issue execution (#72)
- *(config)* Update root directories for fmind, fmind-ai, and mlops-courses
- *(dot)* Unify agent sources, add configurable bounds, simplify bootstrap

### 🐛 Bug Fixes

- *(verify)* Probe CLI capabilities instead of shims
- *(ai)* Pack diffs with explicit omission evidence
- *(agent)* Make session ingestion lineage-safe
- *(prune)* Retain raw sessions until verified
- *(cluster)* Isolate and verify kubeconfig targets
- *(bootstrap)* Verify pinned installers
- *(bootstrap)* Trust nested mise configs hermetically
- *(verify)* Support Helm 4 capability probe (#73)

### ♻️ Refactor

- *(mise)* Separate update and convergence phases

### 🧪 Testing

- *(docs)* Validate agent command contracts
- *(ci)* Validate workflows and skill contracts
## [1.8.0] - 2026-07-31

### 🚀 Features

- *(dot)* Consolidate prune command into dot cli and refine skills
## [1.7.3] - 2026-07-31

### 🐛 Bug Fixes

- *(skills)* Correct inaccurate commands and broken hook ordering

### 🧹 Miscellaneous

- *(prune)* Include the antigravity brain dir in agent transcript pruning
## [1.7.2] - 2026-07-31

### 🐛 Bug Fixes

- *(claude)* Keep Claude Code runtime settings across chezmoi applies

### 🧪 Testing

- *(dot)* Expand unit test coverage across dot cli subcommands
## [1.7.1] - 2026-07-31

### ♻️ Refactor

- *(dot)* Drop the duplicate agent notify subcommand

### 🧹 Miscellaneous

- *(mise)* Re-sync the global lockfile with installed platforms
## [1.7.0] - 2026-07-31

### 🚀 Features

- *(dot)* Notify desktop on agent stop and session end

### 🐛 Bug Fixes

- *(ci)* Lock trivy and restore a green cross-platform pipeline
- *(check)* Render chezmoi against a seeded config so CI can validate it
- *(dot)* Stub the platform browser opener so macOS tests pass

### ♻️ Refactor

- *(dot)* Resolve command alias collisions
## [1.6.0] - 2026-07-31

### 🚀 Features

- Update dot CLI agent tools, dotfiles tasks, and skills

### 🧹 Miscellaneous

- *(claude)* Remove DISABLE_TELEMETRY setting
## [1.5.0] - 2026-07-16

### 🚀 Features

- *(skills)* Add visual and presentation skills
## [1.4.4] - 2026-07-15

### 🧹 Miscellaneous

- *(mise)* Update lockfile
## [1.4.3] - 2026-07-15

### 🧹 Miscellaneous

- Ignore local skills, remove completions hook, update k8s docs
## [1.4.2] - 2026-07-14

### 🧹 Miscellaneous

- *(gh)* Remove prefer_editor_prompt
## [1.4.1] - 2026-07-14

### 📚 Documentation

- *(agents)* Allow direct push to main branch
## [1.4.0] - 2026-07-14

### 🚀 Features

- *(bash)* Add mise activation and paths
## [1.3.0] - 2026-07-14

### 🚀 Features

- *(skills)* Add dependabot skill
## [1.2.4] - 2026-07-13

### 🧹 Miscellaneous

- Configure lsd and disable slsa attestations in mise
## [1.2.3] - 2026-07-13

### ♻️ Refactor

- Replace eza with lsd
## [1.2.2] - 2026-07-12

### 🐛 Bug Fixes

- *(mise)* Pin gws to 0.22.4 for glibc compatibility
## [1.2.1] - 2026-07-12

### 🧹 Miscellaneous

- Add hadolint linter and migrate lazygit config
## [1.2.0] - 2026-07-12

### 🚀 Features

- *(dot)* Add agent session log management command
- *(dot)* Improve CLI commands, tests, and configuration files

### ♻️ Refactor

- *(dot)* Consolidate gcloud login and add python-script skill
## [1.1.1] - 2026-07-08

### ♻️ Refactor

- Trim cliff.toml defaults and dot-release skill
## [1.1.0] - 2026-07-08

### 🚀 Features

- *(dot)* Add release command and html-slides skill
## [1.0.0] - 2026-07-06

### 🚀 Features

- Initial public release
