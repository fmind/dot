---
name: copilot
description: "Copilot CLI sessions, non-interactive flags, folder trust, and extensions."
---

# GitHub Copilot CLI

Operate Copilot CLI; [github-actions](../../github-actions/SKILL.md) owns GitHub Agentic Workflows.

## Workflow

Follow the shared [workflow](../SKILL.md#workflow); host specifics:

- **Headless and parallel runs**: pass `copilot -p "<task>" -s --output-format json` (`-s` drops banners/chrome), `--fleet` for parallel subagent execution, or `copilot acp` / `--acp` for ACP editors.
- **Scopes differ**: keep CLI, IDE, and cloud agent configurations separate.
- **Keep secrets out of argv/output**: pass secret names via `--secret-env-vars=KEY1,KEY2` so Copilot redacts their values from outputs, JSON logs, and tool captures.
- **Separate tool approval from folder trust**: `--allow-all-tools` (without it, `-p` denies unapproved tools) and `COPILOT_ALLOW_ALL=1` only approve tools; setting `COPILOT_ALLOW_ALL=true` also trusts cwd and loads its skills, plugins, MCP servers, and hooks. Prefer `--trust-folder` per reviewed run; `--share-gist` publishes data and requires approval.
- **Managed keys (`fmind/dot`)**: `private_dot_copilot/modify_private_settings.json` (plus `modify_lsp-config.json`) merges `~/.copilot/config.json` (or settings target) with `askUser: true`, `autoUpdate: false`, `defaultMode: "autopilot"`, `editorMode: "vim"`, `notifications: false`, `respectGitignore: false`, and disabled `connectors`/`remoteExport`/`remoteSessions`/`storeTokenPlaintext`; edit sources before `chezmoi apply`.

## Official Skills

- [CLI skills docs](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills) · [Awesome Copilot](https://github.com/github/awesome-copilot) (community-contributed, not first-party; vet before enabling).

## Documentation

- [Copilot CLI documentation](https://docs.github.com/en/copilot/how-tos/copilot-cli) · [Command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference) · [Releases](https://github.com/github/copilot-cli/releases)
