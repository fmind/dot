# AGENTS.md (Project)

This is `fmind/dot` — chezmoi + mise dotfiles for AI-CLI-first, Python-first development on Linux and macOS. Setup and install documentation lives in `README.md`.

## House rules

- **Chezmoi**: Edit the source tree in this repository, never deployed copies under `$HOME`; automation always runs `chezmoi apply --force`. Naming, templates, and secrets: [chezmoi skill](.agents/skills/chezmoi/SKILL.md).
- **Gate**: `mise run all` (format + check + test + build) must pass warning-free before reporting a task complete. It writes files; when unrelated work is present, validate an exact isolated candidate using [git-worktree](skills/git-worktree/SKILL.md).
- **No-Sudo**: Stay user-space; install via `mise`.
- **README Scope**: Keep setup and auth instructions in `README.md`; exclude repository tasks, aliases, and workflows.
- **Secrets**: `*.age` files are encrypted; never modify or commit decrypted versions.
- **Theme**: [fmind/theme](https://github.com/fmind/theme) phosphor green is default across every tool that supports theming, fetched by `.chezmoiexternal.toml.tmpl` and named once by `theme_variant` and `theme_ref` in `.chezmoi.toml.tmpl`. Starship and gh-dash have no include mechanism, so their blocks are copied and marked generated with a link to the upstream file; regenerate them upstream rather than hand-editing. Bumping `theme_ref` needs `chezmoi init` on each machine before the new files are fetched. **Matrix is the look; pragmatic is the rule**: the palette is measured before it ships, and where the vibe and an eight-hour reading day disagree, the reading day wins. Five properties are load bearing:
  - **Fifteen roles, not six.** The bright ANSI half carries independent meanings rather than lightened copies of the normal half, so `warning`, `escape`, `constant`, `parameter`, `builtin` and `property` own slots 9-14 and `punctuation` owns slot 7 — a call, its arguments and the local it returns into are three different colours.
  - **Green carries what you wrote.** Three cool tiers carry what the language knows, amber holds the literals, red and orange the signals, and one violet holds the keyword, which is the only colour no phosphor tube had. An error still reads as an error against a green body.
  - **Bold yes, italic no.** `FiraCode Nerd Font Mono` ships a real Bold face and no italic face at all, so italics would be synthesised by slanting upright glyphs. Keep `bold-is-bright = false`, or bold swaps six semantic roles for six others.
  - **Loud is a defect, not a feature.** Contrast has a ceiling as well as a floor, because WCAG models legibility and not fatigue. The ground sits just off black (`#080b08`) so a saturated body green does not halate, and `string` and `punctuation` — the two roles carrying the most glyphs on any screen — are capped so they recede. Two roles clear 14:1, and the body green is one of them. Never "fix" a colour by making it brighter; `uv run render.py` upstream refuses a palette that drifts back.
  - **Slot 2 is a white, so never ask for "green".** `string` owns ANSI slot 2 and is spent on a near-white, which is correct for a docstring and wrong for everything a tool means by green. Any config that means _ok_, _added_, _new_, _success_ or _executable_ asks for slot 4 (`blue`, the `function` green) instead. Already re-pointed: `lsd/colors.yaml`, `lazygit`, gh-dash's `success`, k9s buttons and breadcrumbs. Known and accepted: yazi's `is = "exec"` rule, which can only be corrected by restating yazi's whole upstream rule list.

  Tools that read the terminal's own sixteen slots follow Ghostty for free, and that is deliberate — one line reskins the lot: `bat --theme=ansi`, lsd, lazygit, lazydocker, bottom, atuin, yazi, fastfetch, gh, ripgrep, jq. Free is not the same as correct, though. A tool's _defaults_ were written for a conventional palette, so check what its named colours actually resolve to here before assuming it landed: lazygit's default focused border is slot 2 (a white) and its unfocused borders are `default` (the neon body green), which is why it now carries a small `gui.theme` block of ANSI names — names, never hex, so the panel still follows whatever Ghostty loads. Where a tool ships its own palette and takes no theme file, pick its most terminal-native option instead — `dark-ansi` for Claude Code, `base16` for mise prompts, `dark` for Grok, which are the only ones that follow the sixteen slots.

  Two tools carry their own icon palettes, and those are left alone: yazi's `[icon]` table and Neovim's `mini.icons`. An icon colour is filetype information, not a semantic role, and overriding either means restating hundreds of entries. The exception was `mini.icons` leaving its nine groups unset, which linked them at _diagnostic_ groups — a Python buffer tab wore the warning colour — so the theme now sets those nine explicitly upstream.

  Zellij is the one tool where handing over the palette makes things worse, and it takes the full named styling block instead. Given the ten-colour form it derives ribbon backgrounds from `fg` and `green`, filling the tab bar with the two brightest colours in the palette for the whole session; no palette edit can reach that.
- **Vim mode**: Enable in every TUI that supports it.

## Workflows

Tasks run via `mise run <task>` (if `mise` is not in `$PATH`, call `~/.local/bin/mise` directly). Invoking tasks from `dot/` resolves to the same root definitions.

Key routines:

- **Iterate**: Edit source → validate with `mise run check` (or `mise run all`) → preview with `mise run diff` → `mise run apply` when deployment is in scope. Apply executes eligible installation hooks as well as writing managed files.
- **Documentation**: `mise run check:docs` checks documentation contracts; `mise run check:skills` checks both skill catalogs and their local links. [repository-docs](skills/repository-docs/SKILL.md) owns documentation synchronization.
- **Workstation vs Gate**: `mise run verify` and `mise run doctor` inspect local workstation health; `mise run check`, `test`, and `all` validate the repository.
- **Add tool**: Append to `dot_config/mise/config.toml.tmpl` → `mise run tools` → `mise run lock`.
- **Upgrade tools**: `mise run upgrade` (upgrades tool pins and lockfiles).
- **Workstation commands**: `dot login`, `setup`, `cache`, and `prune` own native provider operations; mise owns repository installation and validation. Authentication and cleanup are explicit commands, not apply hooks.
- **Usage statistics**: [agent-usage](skills/agent-usage/SKILL.md) owns reports and subscription configuration. Token totals, API equivalents, recorded cost, and subscription charges are separate measurements; preserve immutable generations when changing extraction.
- **CLI (`dot`)**: Follow [dot-development](.agents/skills/dot-development/SKILL.md) for implementation, tests, and installation proof; [dot-cli](skills/dot-cli/SKILL.md) owns command operation.
- **Manage skills**: Follow [dot-skills](.agents/skills/dot-skills/SKILL.md) for global/local catalog changes and validation; [skillify](skills/skillify/SKILL.md) owns authoring conventions.
- **Release**: Follow [dot-release](.agents/skills/dot-release/SKILL.md) for `mise run release`, recovery, and publication verification.

## Agents

- **Persona**: `dot_agents/AGENTS.md` deploys to `~/.agents/AGENTS.md`, consumed by all agent harnesses.
- **Skills**: Global packages live in `skills/`; `dot_agents/skills/symlink_<name>.tmpl` links each into the real `~/.agents/skills/` directory. Other packages use the same directory and remain independently managed. Never use `exact_` for the shared catalog.

## Layout

- `.agents/`, `.antigravitycli/`, `.claude/`, and `.gemini/` hold repository-scoped agent state, links, and local skills.
- `.github/` owns CI, release, security, audit, and dependency-update automation.
- `dot/` contains the runtime package, repository-only `dot_tasks/`, uv lock, and pytest suite.
- `dot_agents/` is the shared persona source; `dot_claude/`, `dot_codex/`, `dot_copilot/`, `dot_cursor/`, `dot_gemini/`, and `dot_grok/` adapt it to each host (with OpenCode in `dot_config/opencode/`).
- `dot_config/` contains managed application configuration; root `dot_*` sources map directly to home targets.
- `modify_dot_bashrc` and `modify_dot_profile` update existing shell files; `run_once_*` and `run_onchange_*` run installation hooks during apply.
- `.chezmoiexternal.toml.tmpl` fetches the theme files from `fmind/theme` during apply, so no palette data is stored in this repository.
- `skills/` is the global Agent Skill catalog shared by every supported host.
- `mise.toml`, `mise.lock`, `lefthook.yml`, and scanner configs define the reproducible repository gate.
- `README.md`, `AGENTS.md`, `CHANGELOG.md`, `LICENSE`, and `install.sh` are the root project contracts and entrypoints.
